/**
 * HTTP client for the Einstein cloud API.
 *
 * All requests include the JWT bearer token from the store.
 * Responses are typed against the domain models in types.ts.
 */
import { useStore } from "../store/useStore";
import type {
  ContextEvent,
  Person,
  Project,
  BriefingData,
  Commitment,
} from "../store/types";

// ---- Helpers ----

function getHeaders(): Record<string, string> {
  const token = useStore.getState().authToken;
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

function baseUrl(): string {
  return useStore.getState().serverUrl;
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${baseUrl()}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: { ...getHeaders(), ...(options.headers || {}) },
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(res.status, body || res.statusText, path);
  }

  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: string,
    public path: string
  ) {
    super(`API ${status} ${path}: ${body}`);
    this.name = "ApiError";
  }
}

// ---- Context Events ----

export async function ingestEvents(
  events: Omit<ContextEvent, "synced">[]
): Promise<{ ingested: number }> {
  for (const event of events) {
    await request("/api/v1/context/ingest", {
      method: "POST",
      body: JSON.stringify(event),
    });
  }
  return { ingested: events.length };
}

export async function getEvents(params?: {
  since?: string;
  source?: string;
  limit?: number;
}): Promise<ContextEvent[]> {
  const qs = new URLSearchParams();
  if (params?.since) qs.set("since", params.since);
  if (params?.source) qs.set("source", params.source);
  if (params?.limit) qs.set("limit", String(params.limit));
  const query = qs.toString();
  return request(`/api/v1/context/events${query ? `?${query}` : ""}`);
}

export async function getTimeline(params?: {
  since?: string;
  until?: string;
  limit?: number;
}): Promise<ContextEvent[]> {
  const qs = new URLSearchParams();
  if (params?.since) qs.set("since", params.since);
  if (params?.until) qs.set("until", params.until);
  if (params?.limit) qs.set("limit", String(params.limit));
  const query = qs.toString();
  return request(`/api/v1/context/timeline${query ? `?${query}` : ""}`);
}

// ---- People ----

export async function getPeople(limit = 50): Promise<Person[]> {
  return request(`/api/v1/context/people?limit=${limit}`);
}

export async function getPersonDossier(
  personId: string
): Promise<Record<string, unknown>> {
  return request(`/api/v1/reflection/people/${personId}/dossier`);
}

// ---- Projects ----

export async function getProjects(status?: string): Promise<Project[]> {
  const qs = status ? `?status=${status}` : "";
  return request(`/api/v1/context/projects${qs}`);
}

// ---- Commitments ----

export async function getCommitments(
  status?: string
): Promise<Commitment[]> {
  const qs = status ? `?status=${status}` : "";
  return request(`/api/v1/insights/commitments${qs}`);
}

// ---- Insights ----

export async function getMorningBriefing(): Promise<BriefingData> {
  return request("/api/v1/insights/briefing/morning");
}

export async function getRelationships(): Promise<Record<string, unknown>[]> {
  return request("/api/v1/reflection/relationships");
}

export async function getWeeklyReview(): Promise<Record<string, unknown>> {
  return request("/api/v1/reflection/review/weekly");
}

// ---- Auth ----

export async function login(
  username: string,
  password: string
): Promise<{ access_token: string }> {
  const res = await fetch(`${baseUrl()}/api/v1/admin/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username, password }).toString(),
  });
  if (!res.ok) throw new ApiError(res.status, "Login failed", "/admin/token");
  return res.json();
}

// ---- Health ----

export async function healthCheck(): Promise<boolean> {
  try {
    await fetch(`${baseUrl()}/api/v1/info`, { method: "GET" });
    return true;
  } catch {
    return false;
  }
}
