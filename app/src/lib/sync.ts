/**
 * Einstein Sync Engine
 *
 * Uses Yjs CRDT for conflict-free collaborative editing.
 * Supports multiple sync providers:
 * 1. Local-only (IndexedDB persistence)
 * 2. File-based sync (Syncthing/iCloud/Dropbox via vault folder)
 * 3. WebSocket relay (Einstein Cloud for real-time collab)
 */

import * as Y from "yjs";
import { IndexeddbPersistence } from "y-indexeddb";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type SyncProvider = "local" | "file" | "cloud";
export type SyncStatus = "idle" | "syncing" | "synced" | "error" | "offline";

export interface SyncState {
  provider: SyncProvider;
  status: SyncStatus;
  lastSynced: Date | null;
  connectedPeers: number;
  error: string | null;
}

export interface CollabUser {
  id: string;
  name: string;
  color: string;
  cursor?: { noteId: string; position: number };
}

// ---------------------------------------------------------------------------
// Sync Manager
// ---------------------------------------------------------------------------

class SyncManager {
  private doc: Y.Doc;
  private persistence: IndexeddbPersistence | null = null;
  private state: SyncState = {
    provider: "local",
    status: "idle",
    lastSynced: null,
    connectedPeers: 0,
    error: null,
  };
  private listeners = new Set<(state: SyncState) => void>();
  private noteTexts = new Map<string, Y.Text>();

  constructor() {
    this.doc = new Y.Doc();
  }

  // --- Lifecycle ---

  async init(vaultId: string, provider: SyncProvider = "local"): Promise<void> {
    this.state.provider = provider;
    this.notifyListeners();

    // Always use IndexedDB for local persistence
    try {
      this.persistence = new IndexeddbPersistence(`einstein-${vaultId}`, this.doc);
      await new Promise<void>((resolve) => {
        this.persistence!.once("synced", () => {
          this.state.status = "synced";
          this.state.lastSynced = new Date();
          this.notifyListeners();
          resolve();
        });
      });
    } catch (err) {
      console.error("IndexedDB persistence failed:", err);
      this.state.status = "error";
      this.state.error = "Failed to initialize local persistence";
      this.notifyListeners();
    }
  }

  destroy(): void {
    this.persistence?.destroy();
    this.doc.destroy();
    this.noteTexts.clear();
    this.listeners.clear();
  }

  // --- Note CRDT Operations ---

  getNoteText(noteId: string): Y.Text {
    if (!this.noteTexts.has(noteId)) {
      const text = this.doc.getText(`note:${noteId}`);
      this.noteTexts.set(noteId, text);
    }
    return this.noteTexts.get(noteId)!;
  }

  updateNoteContent(noteId: string, content: string): void {
    const text = this.getNoteText(noteId);
    this.doc.transact(() => {
      text.delete(0, text.length);
      text.insert(0, content);
    });
    this.state.lastSynced = new Date();
    this.notifyListeners();
  }

  getNoteContent(noteId: string): string {
    return this.getNoteText(noteId).toString();
  }

  deleteNote(noteId: string): void {
    const text = this.getNoteText(noteId);
    this.doc.transact(() => {
      text.delete(0, text.length);
    });
    this.noteTexts.delete(noteId);
  }

  // --- Shared Metadata ---

  getSharedMap(name: string): Y.Map<unknown> {
    return this.doc.getMap(name);
  }

  // Version history via Yjs snapshots
  createSnapshot(): Uint8Array {
    return Y.encodeStateAsUpdate(this.doc);
  }

  applyUpdate(update: Uint8Array): void {
    Y.applyUpdate(this.doc, update);
  }

  // --- Collaboration (future WebSocket provider) ---

  getCollabUsers(): CollabUser[] {
    const awareness = this.getSharedMap("awareness");
    const users: CollabUser[] = [];
    awareness.forEach((value, _key) => {
      if (typeof value === "object" && value !== null) {
        users.push(value as CollabUser);
      }
    });
    return users;
  }

  setLocalUser(user: Omit<CollabUser, "cursor">): void {
    const awareness = this.getSharedMap("awareness");
    awareness.set(user.id, user);
  }

  // --- State Management ---

  getState(): SyncState {
    return { ...this.state };
  }

  subscribe(listener: (state: SyncState) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notifyListeners(): void {
    const snapshot = { ...this.state };
    this.listeners.forEach((fn) => fn(snapshot));
  }

  // --- File-based sync helpers ---

  async exportVaultState(): Promise<string> {
    const update = this.createSnapshot();
    return btoa(String.fromCharCode(...update));
  }

  async importVaultState(base64: string): Promise<void> {
    const binary = atob(base64);
    const update = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      update[i] = binary.charCodeAt(i);
    }
    this.applyUpdate(update);
  }
}

export const syncManager = new SyncManager();

// ---------------------------------------------------------------------------
// React Hook
// ---------------------------------------------------------------------------

import { useState, useEffect } from "react";

export function useSyncState(): SyncState {
  const [syncState, setSyncState] = useState<SyncState>(syncManager.getState());

  useEffect(() => {
    return syncManager.subscribe(setSyncState);
  }, []);

  return syncState;
}
