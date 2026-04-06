/**
 * Core types shared across the mobile app.
 * Mirrors the cloud API domain entities.
 */

export interface ContextEvent {
  id: string;
  user_id: string;
  source: EventSource;
  event_type: string;
  content: string | null;
  timestamp: string; // ISO 8601
  structured_data: Record<string, unknown>;
  extracted_people: string[];
  topics: string[];
  processing_tier: number;
  synced: boolean; // local-only flag for offline support
}

export type EventSource =
  | "notification"
  | "calendar"
  | "contacts"
  | "phone"
  | "manual_note"
  | "email"
  | "sms"
  | "whatsapp"
  | "slack"
  | "gmail"
  | "browser"
  | "shared";

export interface Person {
  id: string;
  name: string;
  aliases: string[];
  phone: string | null;
  email: string | null;
  role: string | null;
  organization: string | null;
  last_seen: string | null;
  interaction_count: number;
  freshness_score: number;
}

export interface Project {
  id: string;
  title: string;
  status: string;
  dormancy_days: number;
  last_activity_at: string | null;
}

export interface Commitment {
  id: string;
  description: string;
  due_date: string | null;
  status: "open" | "fulfilled" | "overdue" | "cancelled";
  person_id: string | null;
}

export interface BriefingData {
  date: string;
  summary: string;
  overdue_commitments: Record<string, unknown>[];
  stale_people: Record<string, unknown>[];
  stale_projects: Record<string, unknown>[];
  today_event_count: number;
  attention_items: string[];
}

export interface SyncStatus {
  lastSyncAt: string | null;
  pendingCount: number;
  isSyncing: boolean;
  error: string | null;
}
