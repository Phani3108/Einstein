/**
 * Offline-first SQLite database.
 *
 * Stores the last 30 days of context events locally.
 * Acts as write-ahead buffer when offline — events sync to cloud when connectivity returns.
 */
import * as SQLite from "expo-sqlite";
import type { ContextEvent } from "../store/types";

const DB_NAME = "einstein_offline.db";
const RETENTION_DAYS = 30;

class OfflineDatabase {
  private db: SQLite.SQLiteDatabase | null = null;

  async open(): Promise<void> {
    if (this.db) return;
    this.db = await SQLite.openDatabaseAsync(DB_NAME);
    await this.migrate();
  }

  private async migrate(): Promise<void> {
    if (!this.db) return;

    await this.db.execAsync(`
      CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        source TEXT NOT NULL,
        event_type TEXT NOT NULL,
        content TEXT,
        timestamp TEXT NOT NULL,
        structured_data TEXT DEFAULT '{}',
        extracted_people TEXT DEFAULT '[]',
        topics TEXT DEFAULT '[]',
        processing_tier INTEGER DEFAULT 0,
        synced INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
      );

      CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
      CREATE INDEX IF NOT EXISTS idx_events_synced ON events(synced);
      CREATE INDEX IF NOT EXISTS idx_events_source ON events(source);

      CREATE TABLE IF NOT EXISTS kv (
        key TEXT PRIMARY KEY,
        value TEXT
      );
    `);
  }

  // ---- Events ----

  async insertEvent(event: ContextEvent): Promise<void> {
    await this.open();
    if (!this.db) return;

    await this.db.runAsync(
      `INSERT OR REPLACE INTO events
        (id, user_id, source, event_type, content, timestamp, structured_data, extracted_people, topics, processing_tier, synced)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        event.id,
        event.user_id,
        event.source,
        event.event_type,
        event.content,
        event.timestamp,
        JSON.stringify(event.structured_data),
        JSON.stringify(event.extracted_people),
        JSON.stringify(event.topics),
        event.processing_tier,
        event.synced ? 1 : 0,
      ]
    );
  }

  async insertEvents(events: ContextEvent[]): Promise<void> {
    for (const event of events) {
      await this.insertEvent(event);
    }
  }

  async getUnsynced(): Promise<ContextEvent[]> {
    await this.open();
    if (!this.db) return [];

    const rows = await this.db.getAllAsync<Record<string, unknown>>(
      "SELECT * FROM events WHERE synced = 0 ORDER BY timestamp DESC"
    );
    return rows.map(rowToEvent);
  }

  async getRecent(limit = 100): Promise<ContextEvent[]> {
    await this.open();
    if (!this.db) return [];

    const rows = await this.db.getAllAsync<Record<string, unknown>>(
      "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?",
      [limit]
    );
    return rows.map(rowToEvent);
  }

  async getBySource(source: string, limit = 50): Promise<ContextEvent[]> {
    await this.open();
    if (!this.db) return [];

    const rows = await this.db.getAllAsync<Record<string, unknown>>(
      "SELECT * FROM events WHERE source = ? ORDER BY timestamp DESC LIMIT ?",
      [source, limit]
    );
    return rows.map(rowToEvent);
  }

  async markSynced(ids: string[]): Promise<void> {
    await this.open();
    if (!this.db || ids.length === 0) return;

    const placeholders = ids.map(() => "?").join(",");
    await this.db.runAsync(
      `UPDATE events SET synced = 1 WHERE id IN (${placeholders})`,
      ids
    );
  }

  async pruneOld(): Promise<number> {
    await this.open();
    if (!this.db) return 0;

    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - RETENTION_DAYS);

    const result = await this.db.runAsync(
      "DELETE FROM events WHERE synced = 1 AND timestamp < ?",
      [cutoff.toISOString()]
    );
    return result.changes;
  }

  async count(): Promise<number> {
    await this.open();
    if (!this.db) return 0;

    const row = await this.db.getFirstAsync<{ count: number }>(
      "SELECT COUNT(*) as count FROM events"
    );
    return row?.count ?? 0;
  }

  // ---- KV Store ----

  async setKV(key: string, value: string): Promise<void> {
    await this.open();
    if (!this.db) return;
    await this.db.runAsync(
      "INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)",
      [key, value]
    );
  }

  async getKV(key: string): Promise<string | null> {
    await this.open();
    if (!this.db) return null;
    const row = await this.db.getFirstAsync<{ value: string }>(
      "SELECT value FROM kv WHERE key = ?",
      [key]
    );
    return row?.value ?? null;
  }
}

function rowToEvent(row: Record<string, unknown>): ContextEvent {
  return {
    id: row.id as string,
    user_id: row.user_id as string,
    source: row.source as ContextEvent["source"],
    event_type: row.event_type as string,
    content: (row.content as string) || null,
    timestamp: row.timestamp as string,
    structured_data: JSON.parse((row.structured_data as string) || "{}"),
    extracted_people: JSON.parse((row.extracted_people as string) || "[]"),
    topics: JSON.parse((row.topics as string) || "[]"),
    processing_tier: (row.processing_tier as number) || 0,
    synced: Boolean(row.synced),
  };
}

/** Singleton */
export const offlineDb = new OfflineDatabase();
