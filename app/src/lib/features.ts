/**
 * Einstein Feature Gating
 *
 * Controls which features are available based on connection mode.
 * Local mode = everything works offline with local AI sidecar.
 * Cloud mode = adds real-time sync, cloud backup, shared canvases.
 */

export type ConnectionMode = "local" | "cloud";

export interface FeatureInfo {
  id: string;
  name: string;
  description: string;
  requiresCloud: boolean;
  requiresAI: boolean;
}

const FEATURES: FeatureInfo[] = [
  // Always available
  { id: "editor", name: "Rich Text Editor", description: "Full markdown editing with wikilinks", requiresCloud: false, requiresAI: false },
  { id: "graph", name: "Knowledge Graph", description: "Visual graph of note connections", requiresCloud: false, requiresAI: false },
  { id: "search", name: "Full-Text Search", description: "Search across all notes", requiresCloud: false, requiresAI: false },
  { id: "backlinks", name: "Backlinks", description: "See which notes link here", requiresCloud: false, requiresAI: false },
  { id: "canvas", name: "Canvas", description: "Visual thinking with tldraw", requiresCloud: false, requiresAI: false },
  { id: "calendar", name: "Calendar", description: "Daily note calendar view", requiresCloud: false, requiresAI: false },
  { id: "kanban", name: "Kanban", description: "Task management board", requiresCloud: false, requiresAI: false },
  { id: "export", name: "Export/Import", description: "Export and import notes", requiresCloud: false, requiresAI: false },
  { id: "plugins", name: "Plugins", description: "Plugin system", requiresCloud: false, requiresAI: false },
  { id: "themes", name: "Themes", description: "Visual customization", requiresCloud: false, requiresAI: false },
  { id: "bookmarks", name: "Bookmarks", description: "Star favorite notes", requiresCloud: false, requiresAI: false },
  { id: "templates", name: "Templates", description: "Create notes from templates", requiresCloud: false, requiresAI: false },
  { id: "versioning", name: "Version History", description: "Restore previous note versions", requiresCloud: false, requiresAI: false },
  { id: "tags", name: "Inline Tags", description: "Parse #tags from note content", requiresCloud: false, requiresAI: false },
  { id: "outline", name: "Outline Panel", description: "Table of contents for notes", requiresCloud: false, requiresAI: false },
  { id: "rename-refactor", name: "Rename Refactoring", description: "Rename notes and update all links", requiresCloud: false, requiresAI: false },

  // Requires AI sidecar (local)
  { id: "entity-extraction", name: "Entity Extraction", description: "AI extracts people, places, topics", requiresCloud: false, requiresAI: true },
  { id: "semantic-search", name: "Semantic Search", description: "Find notes by meaning", requiresCloud: false, requiresAI: true },
  { id: "ai-canvas", name: "AI Canvas Layout", description: "Auto-arrange notes by relationships", requiresCloud: false, requiresAI: true },

  // Requires cloud
  { id: "realtime-sync", name: "Real-Time Sync", description: "Sync notes across devices instantly", requiresCloud: true, requiresAI: false },
  { id: "collaboration", name: "Real-Time Collaboration", description: "Edit notes simultaneously with others", requiresCloud: true, requiresAI: false },
  { id: "cloud-backup", name: "Cloud Backup", description: "Automatic cloud backup of your vault", requiresCloud: true, requiresAI: false },
  { id: "shared-canvas", name: "Shared Canvas", description: "Collaborate on canvases in real-time", requiresCloud: true, requiresAI: false },
  { id: "web-access", name: "Web Access", description: "Access your vault from any browser", requiresCloud: true, requiresAI: false },
];

export function isFeatureAvailable(featureId: string, mode: ConnectionMode, aiAvailable: boolean): boolean {
  const feature = FEATURES.find((f) => f.id === featureId);
  if (!feature) return false;
  if (feature.requiresCloud && mode === "local") return false;
  if (feature.requiresAI && !aiAvailable) return false;
  return true;
}

export function getFeatureGatingMessage(featureId: string, mode: ConnectionMode): string | null {
  const feature = FEATURES.find((f) => f.id === featureId);
  if (!feature) return null;

  if (feature.requiresCloud && mode === "local") {
    return `"${feature.name}" requires cloud mode. You're currently in local-only mode — your data stays entirely on this device.\n\nTo enable this feature:\n1. Go to Settings > Connection Mode\n2. Switch to "Cloud Connected"\n3. Configure your sync provider\n\nYour existing notes will remain untouched. Cloud mode adds sync capabilities without removing local access.`;
  }

  if (feature.requiresAI) {
    return `"${feature.name}" requires the AI sidecar to be running.\n\nTo start the AI sidecar:\n1. Navigate to the sidecar directory\n2. Run: python server.py\n3. Ensure you have an API key configured (OPENAI_API_KEY or ANTHROPIC_API_KEY)\n\nThe AI sidecar runs locally — your notes are never sent to external servers unless you configure a cloud LLM provider.`;
  }

  return null;
}

export function getCloudSwitchingInfo(currentMode: ConnectionMode): {
  canSwitch: boolean;
  steps: string[];
  warnings: string[];
  whatWorks: string[];
  whatDoesnt: string[];
} {
  if (currentMode === "local") {
    return {
      canSwitch: true,
      steps: [
        "Your vault files remain on disk — nothing is deleted",
        "Cloud sync will begin uploading your notes to the configured provider",
        "You can choose which folders to sync (Settings > Sync Folders)",
        "End-to-end encryption is available (Settings > Encryption)",
      ],
      warnings: [
        "First sync may take a few minutes for large vaults",
        "Ensure stable internet connection during initial sync",
        "Notes will be accessible from other devices once sync completes",
      ],
      whatWorks: [
        "Real-time sync across devices",
        "Real-time collaboration with others",
        "Cloud backup with version history",
        "Web access to your vault",
        "All local features continue to work",
      ],
      whatDoesnt: [
        "Editing while completely offline (changes queue until reconnection)",
      ],
    };
  } else {
    return {
      canSwitch: true,
      steps: [
        "Cloud sync will stop — no more uploads or downloads",
        "Your local vault files remain exactly as they are",
        "Any unsynced changes from other devices will not arrive",
        "You can re-enable cloud mode at any time",
      ],
      warnings: [
        "Changes made on other devices after switching won't sync here",
        "Shared canvases will become read-only copies",
        "Collaboration sessions will end",
      ],
      whatWorks: [
        "All editing features",
        "Local AI entity extraction and semantic search",
        "Graph, canvas, calendar, kanban — everything local",
        "Export/import",
        "Plugins and themes",
      ],
      whatDoesnt: [
        "Real-time sync",
        "Real-time collaboration",
        "Cloud backup",
        "Web access",
      ],
    };
  }
}

export function getAllFeatures(): FeatureInfo[] {
  return [...FEATURES];
}
