/**
 * CalendarCollector — reads upcoming calendar events via expo-calendar.
 *
 * - Syncs on launch + every hour.
 * - Captures next 30 days of events.
 * - Deduplicates by calendar event ID.
 * - Extracts attendee names for entity linking.
 */
import * as Calendar from "expo-calendar";
import { useStore } from "../../store/useStore";
import { extractTier0 } from "../tier0";
import { offlineDb } from "../../db/offline";
import type { ContextEvent } from "../../store/types";

const LOOK_AHEAD_DAYS = 30;

export async function collectCalendarEvents(): Promise<number> {
  const { status } = await Calendar.requestCalendarPermissionsAsync();
  if (status !== "granted") {
    console.warn("[CalendarCollector] Permission denied");
    return 0;
  }

  const calendars = await Calendar.getCalendarsAsync(Calendar.EntityTypes.EVENT);
  const calendarIds = calendars.map((c) => c.id);
  if (calendarIds.length === 0) return 0;

  const now = new Date();
  const end = new Date();
  end.setDate(end.getDate() + LOOK_AHEAD_DAYS);

  const events = await Calendar.getEventsAsync(calendarIds, now, end);

  let ingested = 0;
  for (const cal of events) {
    const eventId = `cal_${cal.id}`;

    // Build content string
    const parts = [cal.title];
    if (cal.location) parts.push(`at ${cal.location}`);
    if (cal.notes) parts.push(cal.notes);
    const content = parts.join(" — ");

    // Extract attendee names
    const attendees = (cal.attendees ?? [])
      .map((a) => a.name || a.email || "")
      .filter(Boolean);

    const tier0 = extractTier0(content);

    const contextEvent: ContextEvent = {
      id: eventId,
      user_id: "",
      source: "calendar",
      event_type: "calendar_event",
      content,
      timestamp: cal.startDate
        ? new Date(cal.startDate).toISOString()
        : now.toISOString(),
      structured_data: {
        calendar_id: cal.calendarId,
        title: cal.title,
        location: cal.location,
        start_date: cal.startDate,
        end_date: cal.endDate,
        all_day: cal.allDay,
        attendees,
        recurrence: cal.recurrenceRule,
        ...tier0,
      },
      extracted_people: [...new Set([...attendees, ...tier0.extracted_people])],
      topics: [],
      processing_tier: 0,
      synced: false,
    };

    await offlineDb.insertEvent(contextEvent);
    useStore.getState().addEvent(contextEvent);
    ingested++;
  }

  console.log(`[CalendarCollector] Ingested ${ingested} events`);
  return ingested;
}
