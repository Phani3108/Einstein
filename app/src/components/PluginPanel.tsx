import { useState, useCallback } from "react";
import { pluginRegistry } from "../lib/plugins";
import type { Plugin } from "../lib/plugins";
import { Settings, ToggleLeft, ToggleRight, Palette, Cpu, Layout } from "lucide-react";

const TYPE_ICONS: Record<string, React.ReactNode> = {
  processing: <Cpu size={14} />,
  ui: <Layout size={14} />,
  theme: <Palette size={14} />,
};

export function PluginPanel() {
  const [plugins, setPlugins] = useState<Plugin[]>(() => pluginRegistry.getAll());
  const [filter, setFilter] = useState<string>("all");

  const togglePlugin = useCallback((id: string) => {
    const plugin = plugins.find((p) => p.id === id);
    if (!plugin) return;
    pluginRegistry.toggle(id, !plugin.enabled);
    setPlugins([...pluginRegistry.getAll()]);
  }, [plugins]);

  const filtered = filter === "all"
    ? plugins
    : plugins.filter((p) => p.type === filter);

  return (
    <div className="plugin-panel">
      <div className="plugin-header">
        <Settings size={16} />
        <h3>Plugins</h3>
      </div>

      <div className="plugin-filters">
        {["all", "processing", "ui", "theme"].map((f) => (
          <button
            key={f}
            className={`plugin-filter-btn ${filter === f ? "active" : ""}`}
            onClick={() => setFilter(f)}
          >
            {f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      <div className="plugin-list">
        {filtered.map((plugin) => (
          <div key={plugin.id} className="plugin-card">
            <div className="plugin-card-header">
              <div className="plugin-card-icon">
                {TYPE_ICONS[plugin.type]}
              </div>
              <div className="plugin-card-info">
                <div className="plugin-card-name">{plugin.name}</div>
                <div className="plugin-card-version">v{plugin.version}</div>
              </div>
              <button
                className={`plugin-toggle ${plugin.enabled ? "enabled" : ""}`}
                onClick={() => togglePlugin(plugin.id)}
              >
                {plugin.enabled ? (
                  <ToggleRight size={20} />
                ) : (
                  <ToggleLeft size={20} />
                )}
              </button>
            </div>
            <div className="plugin-card-desc">{plugin.description}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
