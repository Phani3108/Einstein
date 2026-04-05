/**
 * Einstein Plugin System
 *
 * Supports three plugin types:
 * 1. UI Plugins — React components rendered in designated slots
 * 2. Processing Plugins — hooks that run on note save/load events
 * 3. Theme Plugins — CSS custom properties overrides
 */

import type { Note } from "./api";

// ---------------------------------------------------------------------------
// Plugin Types
// ---------------------------------------------------------------------------

export type PluginType = "ui" | "processing" | "theme";

export interface PluginManifest {
  id: string;
  name: string;
  version: string;
  description: string;
  type: PluginType;
  author?: string;
  enabled: boolean;
}

// Event hooks for processing plugins
export type PluginEvent =
  | "on_note_save"
  | "on_note_load"
  | "on_note_delete"
  | "on_vault_open"
  | "on_search";

export interface ProcessingPlugin extends PluginManifest {
  type: "processing";
  hooks: Partial<Record<PluginEvent, (data: PluginEventData) => Promise<PluginEventData>>>;
}

export interface UIPlugin extends PluginManifest {
  type: "ui";
  slot: "sidebar" | "right-panel" | "toolbar" | "status-bar" | "main";
  render: () => React.ReactNode;
}

export interface ThemePlugin extends PluginManifest {
  type: "theme";
  variables: Record<string, string>;
}

export type Plugin = ProcessingPlugin | UIPlugin | ThemePlugin;

export interface PluginEventData {
  note?: Note;
  notes?: Note[];
  query?: string;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Plugin Registry
// ---------------------------------------------------------------------------

class PluginRegistry {
  private plugins = new Map<string, Plugin>();
  private hooks = new Map<PluginEvent, Array<{ pluginId: string; handler: (data: PluginEventData) => Promise<PluginEventData> }>>();

  register(plugin: Plugin): void {
    this.plugins.set(plugin.id, plugin);

    if (plugin.type === "processing") {
      for (const [event, handler] of Object.entries(plugin.hooks)) {
        if (!handler) continue;
        const eventKey = event as PluginEvent;
        if (!this.hooks.has(eventKey)) {
          this.hooks.set(eventKey, []);
        }
        this.hooks.get(eventKey)!.push({ pluginId: plugin.id, handler });
      }
    }

    if (plugin.type === "theme" && plugin.enabled) {
      this.applyTheme(plugin);
    }
  }

  unregister(pluginId: string): void {
    const plugin = this.plugins.get(pluginId);
    if (!plugin) return;

    // Remove hooks
    for (const [event, handlers] of this.hooks) {
      this.hooks.set(
        event,
        handlers.filter((h) => h.pluginId !== pluginId)
      );
    }

    // Remove theme
    if (plugin.type === "theme") {
      this.removeTheme(plugin);
    }

    this.plugins.delete(pluginId);
  }

  toggle(pluginId: string, enabled: boolean): void {
    const plugin = this.plugins.get(pluginId);
    if (!plugin) return;
    plugin.enabled = enabled;

    if (plugin.type === "theme") {
      if (enabled) this.applyTheme(plugin);
      else this.removeTheme(plugin);
    }
  }

  async emit(event: PluginEvent, data: PluginEventData): Promise<PluginEventData> {
    const handlers = this.hooks.get(event) ?? [];
    let result = data;
    for (const { pluginId, handler } of handlers) {
      const plugin = this.plugins.get(pluginId);
      if (!plugin?.enabled) continue;
      try {
        result = await handler(result);
      } catch (err) {
        console.error(`Plugin ${pluginId} error on ${event}:`, err);
      }
    }
    return result;
  }

  getUIPlugins(slot: UIPlugin["slot"]): UIPlugin[] {
    return Array.from(this.plugins.values()).filter(
      (p): p is UIPlugin => p.type === "ui" && p.enabled && (p as UIPlugin).slot === slot
    );
  }

  getAll(): Plugin[] {
    return Array.from(this.plugins.values());
  }

  private applyTheme(plugin: ThemePlugin): void {
    const root = document.documentElement;
    for (const [key, value] of Object.entries(plugin.variables)) {
      root.style.setProperty(key, value);
    }
  }

  private removeTheme(plugin: ThemePlugin): void {
    const root = document.documentElement;
    for (const key of Object.keys(plugin.variables)) {
      root.style.removeProperty(key);
    }
  }
}

export const pluginRegistry = new PluginRegistry();

// ---------------------------------------------------------------------------
// Built-in Plugins
// ---------------------------------------------------------------------------

/** Word Count Plugin — shows word count in status bar */
export const wordCountPlugin: ProcessingPlugin = {
  id: "einstein.word-count",
  name: "Word Count",
  version: "1.0.0",
  description: "Tracks word count statistics",
  type: "processing",
  enabled: true,
  hooks: {
    on_note_save: async (data) => {
      if (data.note) {
        const words = data.note.content.split(/\s+/).filter(Boolean).length;
        console.log(`[WordCount] ${data.note.title}: ${words} words`);
      }
      return data;
    },
  },
};

/** Auto-Tag Plugin — adds tags based on content keywords */
export const autoTagPlugin: ProcessingPlugin = {
  id: "einstein.auto-tag",
  name: "Auto Tag",
  version: "1.0.0",
  description: "Automatically suggests tags based on note content",
  type: "processing",
  enabled: true,
  hooks: {
    on_note_save: async (data) => {
      // Auto-tagging logic would go here
      return data;
    },
  },
};

/** Dark Blue Theme */
export const darkBlueTheme: ThemePlugin = {
  id: "einstein.theme-dark-blue",
  name: "Dark Blue",
  version: "1.0.0",
  description: "A deep blue dark theme",
  type: "theme",
  enabled: false,
  variables: {
    "--bg-primary": "#0a0e1a",
    "--bg-secondary": "#101525",
    "--bg-tertiary": "#161b30",
    "--bg-base": "#080c16",
    "--bg-elevated": "#121830",
    "--bg-surface": "#0e1325",
    "--bg-hover": "rgba(79, 125, 245, 0.1)",
    "--bg-active": "rgba(79, 125, 245, 0.15)",
    "--bg-selected": "rgba(79, 125, 245, 0.2)",
    "--bg-sidebar": "#0a0e1a",
    "--text-primary": "#e0e4f0",
    "--text-secondary": "#8890b0",
    "--text-tertiary": "#5560a0",
    "--border": "rgba(79, 125, 245, 0.15)",
    "--border-strong": "rgba(79, 125, 245, 0.3)",
    "--accent": "#4f7df5",
    "--accent-hover": "#3a6df0",
  },
};

/** Warm Dark Theme */
export const warmDarkTheme: ThemePlugin = {
  id: "einstein.theme-warm-dark",
  name: "Warm Dark",
  version: "1.0.0",
  description: "A warm, sepia-tinted dark theme",
  type: "theme",
  enabled: false,
  variables: {
    "--bg-primary": "#1a1612",
    "--bg-secondary": "#221e19",
    "--bg-tertiary": "#2a2520",
    "--bg-base": "#151210",
    "--bg-elevated": "#2a2420",
    "--bg-surface": "#201c18",
    "--bg-hover": "rgba(212, 165, 116, 0.1)",
    "--bg-active": "rgba(212, 165, 116, 0.15)",
    "--bg-selected": "rgba(212, 165, 116, 0.2)",
    "--bg-sidebar": "#1a1612",
    "--text-primary": "#e8ddd0",
    "--text-secondary": "#a09080",
    "--text-tertiary": "#706050",
    "--border": "rgba(212, 165, 116, 0.15)",
    "--border-strong": "rgba(212, 165, 116, 0.3)",
    "--accent": "#d4a574",
    "--accent-hover": "#c49564",
  },
};

/** Light Theme */
export const lightTheme: ThemePlugin = {
  id: "einstein.theme-light",
  name: "Light",
  version: "1.0.0",
  description: "A clean light theme for daytime use",
  type: "theme",
  enabled: false,
  variables: {
    "--bg-primary": "#ffffff",
    "--bg-secondary": "#f5f5f5",
    "--bg-tertiary": "#ebebeb",
    "--bg-base": "#fafafa",
    "--bg-elevated": "#ffffff",
    "--bg-surface": "#f0f0f0",
    "--bg-hover": "rgba(0, 0, 0, 0.04)",
    "--bg-active": "rgba(0, 0, 0, 0.06)",
    "--bg-selected": "rgba(59, 130, 246, 0.1)",
    "--bg-sidebar": "#f5f5f5",
    "--text-primary": "#1a1a1a",
    "--text-secondary": "#666666",
    "--text-tertiary": "#999999",
    "--border": "rgba(0, 0, 0, 0.08)",
    "--border-strong": "rgba(0, 0, 0, 0.15)",
    "--accent": "#3b82f6",
    "--accent-hover": "#2563eb",
  },
};

// Register built-in plugins
pluginRegistry.register(wordCountPlugin);
pluginRegistry.register(autoTagPlugin);
pluginRegistry.register(darkBlueTheme);
pluginRegistry.register(warmDarkTheme);
pluginRegistry.register(lightTheme);
