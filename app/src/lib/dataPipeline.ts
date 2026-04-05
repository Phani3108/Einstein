/**
 * dataPipeline.ts — Unified Data Pipeline for Einstein
 *
 * SINGLE entry point for ALL data entering the system.
 * Every note save, meeting import, data exchange import, voice transcript,
 * and "Save as Note" action flows through this pipeline.
 *
 * Pipeline stages:
 *   1. Save note to vault (Tauri IPC)
 *   2. Entity extraction (sidecar /extract)
 *   3. Action item + calendar event extraction (sidecar /extract-actions)
 *   4. Persist action items to DB (api.saveActionItems)
 *   5. Persist calendar events to DB (api.saveCalendarEvents)
 *   6. RAG re-index this note (api.ragIndex)
 *   7. Update central state via dispatch
 *   8. Emit plugin hooks
 */

import { api } from "./api";
import type { Note, ActionItemData, CalendarEventData } from "./api";
import type { AppAction, ActionItemState, CalendarEventState } from "./store";
import { pluginRegistry } from "./plugins";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface PipelineOptions {
  /** Skip AI extraction (entity + action items). Use for bulk imports. */
  skipAI?: boolean;
  /** Skip RAG re-indexing. Use when doing a full vault re-index separately. */
  skipRAG?: boolean;
  /** Source label for provenance tracking */
  source?: string;
  /** If true, the note is already saved — skip stage 1 */
  alreadySaved?: boolean;
}

export interface PipelineResult {
  note: Note;
  entitiesExtracted: number;
  actionItemsExtracted: number;
  calendarEventsExtracted: number;
  errors: string[];
}

export type PipelineDispatch = React.Dispatch<AppAction>;

/* ------------------------------------------------------------------ */
/*  Pipeline status callback (for UI feedback)                         */
/* ------------------------------------------------------------------ */

export type PipelineStage =
  | "saving"
  | "extracting-entities"
  | "extracting-actions"
  | "persisting"
  | "indexing"
  | "done";

export type PipelineStatusCallback = (stage: PipelineStage) => void;

/* ------------------------------------------------------------------ */
/*  Main pipeline function                                             */
/* ------------------------------------------------------------------ */

export async function processNoteThroughPipeline(
  note: Note,
  dispatch: PipelineDispatch,
  options: PipelineOptions = {},
  onStatus?: PipelineStatusCallback,
): Promise<PipelineResult> {
  const result: PipelineResult = {
    note,
    entitiesExtracted: 0,
    actionItemsExtracted: 0,
    calendarEventsExtracted: 0,
    errors: [],
  };

  dispatch({ type: "SET_PIPELINE_RUNNING", running: true });

  try {
    // ------------------------------------------------------------------
    // Stage 1: Save note (if not already saved)
    // ------------------------------------------------------------------
    if (!options.alreadySaved) {
      onStatus?.("saving");
      try {
        const saved = await api.saveNote(
          note.file_path,
          note.title,
          note.content,
          note.frontmatter,
        );
        result.note = saved;
        dispatch({ type: "UPDATE_NOTE", note: saved });
        pluginRegistry.emit("on_note_save", { note: saved });
      } catch (err) {
        result.errors.push(`Save failed: ${err}`);
        dispatch({ type: "SET_PIPELINE_RUNNING", running: false });
        return result;
      }
    }

    const currentNote = result.note;
    const content = currentNote.content;

    // Skip AI stages if content is too short or flag is set
    const shouldRunAI = !options.skipAI && content.trim().length > 20;

    if (shouldRunAI) {
      // ----------------------------------------------------------------
      // Stage 2: Entity extraction
      // ----------------------------------------------------------------
      onStatus?.("extracting-entities");
      try {
        const entities = await api.extractEntities(content, currentNote.id);
        result.entitiesExtracted = entities.length;

        if (entities.length > 0) {
          // Persist entities in frontmatter
          const updatedFrontmatter = {
            ...currentNote.frontmatter,
            entities: JSON.stringify(entities),
          };
          const updated = await api.saveNote(
            currentNote.file_path,
            currentNote.title,
            content,
            updatedFrontmatter,
          );
          result.note = updated;
          dispatch({ type: "UPDATE_NOTE", note: updated });
        }
      } catch (err) {
        result.errors.push(`Entity extraction failed: ${err}`);
        // Non-fatal — continue pipeline
      }

      // ----------------------------------------------------------------
      // Stage 3: Action item + calendar event extraction
      // ----------------------------------------------------------------
      onStatus?.("extracting-actions");
      try {
        const extracted = await api.extractActions(
          content,
          currentNote.id,
          currentNote.title,
        );

        const actionItems: ActionItemData[] = (extracted.action_items || []).map(
          (item: Record<string, unknown>) => ({
            task: String(item.task || ""),
            assignee: item.assignee ? String(item.assignee) : null,
            deadline: item.deadline ? String(item.deadline) : null,
            priority: (item.priority as "high" | "medium" | "low") || "medium",
            status: "pending",
          }),
        );

        const calendarEvents: CalendarEventData[] = (extracted.calendar_events || []).map(
          (ev: Record<string, unknown>) => ({
            title: String(ev.title || ""),
            event_date: String(ev.event_date || ""),
            event_type: (ev.event_type as CalendarEventData["event_type"]) || "reminder",
            description: String(ev.description || ""),
          }),
        );

        result.actionItemsExtracted = actionItems.length;
        result.calendarEventsExtracted = calendarEvents.length;

        // ----------------------------------------------------------------
        // Stage 4: Persist action items to DB
        // ----------------------------------------------------------------
        onStatus?.("persisting");
        if (actionItems.length > 0) {
          try {
            await api.saveActionItems(currentNote.id, actionItems);
          } catch (err) {
            result.errors.push(`Save action items failed: ${err}`);
          }
        }

        // ----------------------------------------------------------------
        // Stage 5: Persist calendar events to DB
        // ----------------------------------------------------------------
        if (calendarEvents.length > 0) {
          try {
            await api.saveCalendarEvents(currentNote.id, calendarEvents);
          } catch (err) {
            result.errors.push(`Save calendar events failed: ${err}`);
          }
        }

        // ----------------------------------------------------------------
        // Stage 6: Update central state
        // ----------------------------------------------------------------
        // Re-fetch from DB to get server-generated IDs and timestamps
        try {
          const dbItems = await api.getActionItems(currentNote.id);
          const actionItemStates: ActionItemState[] = dbItems.map((item) => ({
            id: item.id,
            note_id: item.note_id,
            task: item.task,
            assignee: item.assignee,
            deadline: item.deadline,
            priority: item.priority as ActionItemState["priority"],
            status: item.status as ActionItemState["status"],
            created_at: item.created_at,
            source_title: currentNote.title,
          }));
          dispatch({ type: "ADD_ACTION_ITEMS", items: actionItemStates });
        } catch {
          // If re-fetch fails, still update with what we have
        }

        try {
          // Fetch calendar events for a wide range to get the ones we just saved
          const dbEvents = await api.getCalendarEvents("2020-01-01", "2030-12-31");
          const noteEvents = dbEvents.filter((e) => e.note_id === currentNote.id);
          const calEventStates: CalendarEventState[] = noteEvents.map((ev) => ({
            id: ev.id,
            note_id: ev.note_id,
            title: ev.title,
            event_date: ev.event_date,
            event_type: ev.event_type as CalendarEventState["event_type"],
            description: ev.description,
            created_at: ev.created_at,
            source_title: currentNote.title,
          }));
          dispatch({ type: "ADD_CALENDAR_EVENTS", events: calEventStates });
        } catch {
          // Non-fatal
        }

        // Also persist action items in frontmatter for offline access
        if (actionItems.length > 0) {
          try {
            const updatedFrontmatter = {
              ...result.note.frontmatter,
              action_items: JSON.stringify(actionItems),
            };
            const updated = await api.saveNote(
              result.note.file_path,
              result.note.title,
              content,
              updatedFrontmatter,
            );
            result.note = updated;
            dispatch({ type: "UPDATE_NOTE", note: updated });
          } catch {
            // Non-fatal
          }
        }
      } catch (err) {
        result.errors.push(`Action extraction failed: ${err}`);
      }
    }

    // ------------------------------------------------------------------
    // Stage 7: RAG re-index
    // ------------------------------------------------------------------
    if (!options.skipRAG) {
      onStatus?.("indexing");
      try {
        await api.ragIndex([
          {
            id: result.note.id,
            title: result.note.title,
            content: result.note.content,
          },
        ]);
      } catch (err) {
        result.errors.push(`RAG indexing failed: ${err}`);
      }
    }

    // ------------------------------------------------------------------
    // Stage 8: Plugin hooks
    // ------------------------------------------------------------------
    pluginRegistry.emit("on_pipeline_complete", {
      note: result.note,
      source: options.source || "editor",
      entitiesExtracted: result.entitiesExtracted,
      actionItemsExtracted: result.actionItemsExtracted,
      calendarEventsExtracted: result.calendarEventsExtracted,
    });

    onStatus?.("done");
  } finally {
    dispatch({ type: "SET_PIPELINE_RUNNING", running: false });
  }

  return result;
}

/* ------------------------------------------------------------------ */
/*  Convenience: Create a new note and run it through the pipeline      */
/* ------------------------------------------------------------------ */

export async function createNoteAndProcess(
  title: string,
  content: string,
  dispatch: PipelineDispatch,
  options: PipelineOptions = {},
): Promise<PipelineResult> {
  const filePath = `${title.replace(/\s+/g, "-").toLowerCase()}.md`;
  const note: Note = {
    id: "", // will be set by saveNote
    file_path: filePath,
    title,
    content,
    frontmatter: {},
    outgoing_links: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  return processNoteThroughPipeline(note, dispatch, options);
}

/* ------------------------------------------------------------------ */
/*  Bulk load: Hydrate central state from DB on vault open              */
/* ------------------------------------------------------------------ */

export async function loadCentralState(
  dispatch: PipelineDispatch,
  notes: Note[],
): Promise<void> {
  const noteTitleMap = new Map(notes.map((n) => [n.id, n.title]));

  // Load all action items from DB
  try {
    const dbItems = await api.getActionItems();
    const actionItems: ActionItemState[] = dbItems.map((item) => ({
      id: item.id,
      note_id: item.note_id,
      task: item.task,
      assignee: item.assignee,
      deadline: item.deadline,
      priority: item.priority as ActionItemState["priority"],
      status: item.status as ActionItemState["status"],
      created_at: item.created_at,
      source_title: noteTitleMap.get(item.note_id) || "Unknown",
    }));
    dispatch({ type: "SET_ACTION_ITEMS", items: actionItems });
  } catch (err) {
    console.error("Failed to load action items:", err);
  }

  // Load all calendar events from DB
  try {
    const dbEvents = await api.getCalendarEvents("2020-01-01", "2030-12-31");
    const calEvents: CalendarEventState[] = dbEvents.map((ev) => ({
      id: ev.id,
      note_id: ev.note_id,
      title: ev.title,
      event_date: ev.event_date,
      event_type: ev.event_type as CalendarEventState["event_type"],
      description: ev.description,
      created_at: ev.created_at,
      source_title: noteTitleMap.get(ev.note_id) || "Unknown",
    }));
    dispatch({ type: "SET_CALENDAR_EVENTS", events: calEvents });
  } catch (err) {
    console.error("Failed to load calendar events:", err);
  }

  // Background RAG index (non-blocking)
  api.ragIndex(
    notes.map((n) => ({ id: n.id, title: n.title, content: n.content })),
  ).catch((err) => console.error("Background RAG index failed:", err));
}
