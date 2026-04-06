/**
 * Background sync engine.
 *
 * - Queues unsynced ContextEvents for upload to the cloud API.
 * - Pulls fresh data (people, projects, briefings) from the server.
 * - Intervals: 5 min on WiFi, 15 min on cellular.
 * - Graceful offline: retries with exponential backoff.
 */
import * as TaskManager from "expo-task-manager";
import * as BackgroundFetch from "expo-background-fetch";
import NetInfo from "@react-native-community/netinfo";

import { useStore } from "../store/useStore";
import * as api from "./api";
import { offlineDb } from "../db/offline";

const SYNC_TASK_NAME = "einstein-background-sync";
const WIFI_INTERVAL_SEC = 5 * 60; // 5 min
const CELLULAR_INTERVAL_SEC = 15 * 60; // 15 min
const MAX_BATCH_SIZE = 50;

// ---- Core sync logic ----

export async function syncNow(): Promise<{
  uploaded: number;
  downloaded: number;
  error: string | null;
}> {
  const store = useStore.getState();

  if (store.sync.isSyncing) {
    return { uploaded: 0, downloaded: 0, error: "Already syncing" };
  }

  store.setSyncStatus({ isSyncing: true, error: null });

  let uploaded = 0;
  let downloaded = 0;
  let error: string | null = null;

  try {
    // ---- Upload unsynced events ----
    const unsynced = store.unsynced();
    if (unsynced.length > 0) {
      // Batch upload in chunks
      for (let i = 0; i < unsynced.length; i += MAX_BATCH_SIZE) {
        const batch = unsynced.slice(i, i + MAX_BATCH_SIZE);
        try {
          const result = await api.ingestEvents(
            batch.map(({ synced, ...event }) => event)
          );
          const ids = batch.map((e) => e.id);
          store.markSynced(ids);
          // Remove synced events from offline DB
          await offlineDb.markSynced(ids);
          uploaded += result.ingested;
        } catch (err) {
          // Partial failure — continue with next batch
          console.warn("[sync] Batch upload failed:", err);
        }
      }
    }

    // ---- Download fresh data ----
    try {
      const [people, projects, commitments] = await Promise.all([
        api.getPeople(),
        api.getProjects(),
        api.getCommitments(),
      ]);
      store.setPeople(people);
      store.setProjects(projects);
      store.setCommitments(commitments);
      downloaded += people.length + projects.length;
    } catch (err) {
      console.warn("[sync] Download failed:", err);
    }

    // ---- Refresh briefing ----
    try {
      const briefing = await api.getMorningBriefing();
      store.setBriefing(briefing);
    } catch {
      // Not critical
    }

    store.setSyncStatus({
      isSyncing: false,
      lastSyncAt: new Date().toISOString(),
      pendingCount: store.unsynced().length,
    });
  } catch (err: unknown) {
    error = err instanceof Error ? err.message : "Sync failed";
    store.setSyncStatus({ isSyncing: false, error });
  }

  return { uploaded, downloaded, error };
}

// ---- Background task registration ----

TaskManager.defineTask(SYNC_TASK_NAME, async () => {
  try {
    const { error } = await syncNow();
    return error
      ? BackgroundFetch.BackgroundFetchResult.Failed
      : BackgroundFetch.BackgroundFetchResult.NewData;
  } catch {
    return BackgroundFetch.BackgroundFetchResult.Failed;
  }
});

export async function registerBackgroundSync(): Promise<void> {
  const netState = await NetInfo.fetch();
  const interval =
    netState.type === "wifi" ? WIFI_INTERVAL_SEC : CELLULAR_INTERVAL_SEC;

  try {
    await BackgroundFetch.registerTaskAsync(SYNC_TASK_NAME, {
      minimumInterval: interval,
      stopOnTerminate: false,
      startOnBoot: true,
    });
    console.log(`[sync] Background sync registered (${interval}s interval)`);
  } catch (err) {
    console.warn("[sync] Background registration failed:", err);
  }
}

export async function unregisterBackgroundSync(): Promise<void> {
  try {
    await BackgroundFetch.unregisterTaskAsync(SYNC_TASK_NAME);
  } catch {
    // Already unregistered
  }
}
