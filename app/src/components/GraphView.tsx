import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import Graph from "graphology";
import Sigma from "sigma";
import forceAtlas2 from "graphology-layout-forceatlas2";
import { useApp } from "../lib/store";
import { api } from "../lib/api";
import type { GraphData } from "../lib/api";
import {
  RefreshCw,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Focus,
  Layers,
} from "lucide-react";

const NODE_COLORS: Record<string, string> = {
  note: "#3b82f6",
  person: "#a78bfa",
  location: "#14b8a6",
  organization: "#60a5fa",
  activity: "#22c55e",
  emotion: "#ec4899",
  event: "#eab308",
  date: "#f97316",
};

const EDGE_COLORS: Record<string, string> = {
  wikilink: "#3b82f6",
  entity: "rgba(255,255,255,0.12)",
};

type GraphMode = "global" | "local";

export function GraphView() {
  const { state, dispatch } = useApp();
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<GraphMode>("global");
  const [activeFilters, setActiveFilters] = useState<Set<string>>(
    new Set(Object.keys(NODE_COLORS))
  );
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const notesRef = useRef(state.notes);
  notesRef.current = state.notes;

  const fetchGraph = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getGraphData();
      setGraphData(data);
    } catch (err) {
      console.error("Failed to fetch graph:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  // Filter graph data based on active filters and mode
  const filteredData = useMemo(() => {
    if (!graphData) return null;

    let nodes = graphData.nodes.filter((n) => activeFilters.has(n.node_type));
    const nodeIds = new Set(nodes.map((n) => n.id));

    // Local mode: only show nodes connected to the active note
    if (mode === "local" && state.activeNoteId) {
      const activeNote = state.notes.find((n) => n.id === state.activeNoteId);
      if (activeNote) {
        const connectedIds = new Set<string>();
        // Find the graph node for the active note
        const activeGraphNode = graphData.nodes.find(
          (n) => n.file_path === activeNote.file_path
        );
        if (activeGraphNode) {
          connectedIds.add(activeGraphNode.id);
          // Find all nodes connected via edges
          for (const edge of graphData.edges) {
            if (edge.source === activeGraphNode.id && nodeIds.has(edge.target)) {
              connectedIds.add(edge.target);
            }
            if (edge.target === activeGraphNode.id && nodeIds.has(edge.source)) {
              connectedIds.add(edge.source);
            }
          }
        }
        nodes = nodes.filter((n) => connectedIds.has(n.id));
      }
    }

    const filteredNodeIds = new Set(nodes.map((n) => n.id));
    const edges = graphData.edges.filter(
      (e) => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)
    );

    return { nodes, edges };
  }, [graphData, activeFilters, mode, state.activeNoteId, state.notes]);

  useEffect(() => {
    if (!containerRef.current || !filteredData) return;

    if (sigmaRef.current) {
      sigmaRef.current.kill();
      sigmaRef.current = null;
    }

    const graph = new Graph();

    filteredData.nodes.forEach((node, i) => {
      const angle = (i / Math.max(filteredData.nodes.length, 1)) * 2 * Math.PI;
      const radius = 50 + Math.random() * 30;
      graph.addNode(node.id, {
        label: node.label,
        x: Math.cos(angle) * radius,
        y: Math.sin(angle) * radius,
        size: node.node_type === "note" ? 8 : 5,
        color: NODE_COLORS[node.node_type] || "#555",
        type: "circle",
      });
    });

    const edgeSet = new Set<string>();
    for (const edge of filteredData.edges) {
      const key = `${edge.source}→${edge.target}`;
      if (edgeSet.has(key)) continue;
      edgeSet.add(key);
      if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
        graph.addEdge(edge.source, edge.target, {
          color: EDGE_COLORS[edge.edge_type] || "rgba(255,255,255,0.05)",
          size: edge.edge_type === "wikilink" ? 1.5 : 0.5,
        });
      }
    }

    if (graph.order > 1) {
      forceAtlas2.assign(graph, {
        iterations: 150,
        settings: {
          gravity: 2,
          scalingRatio: 8,
          barnesHutOptimize: graph.order > 100,
          strongGravityMode: true,
        },
      });
    }

    const renderer = new Sigma(graph, containerRef.current, {
      renderLabels: true,
      labelColor: { color: "#e0e0e0" },
      labelFont: "-apple-system, sans-serif",
      labelSize: 11,
      labelWeight: "500",
      defaultEdgeColor: "rgba(255,255,255,0.05)",
      defaultNodeColor: "#3b82f6",
      labelRenderedSizeThreshold: 4,
    });

    renderer.on("clickNode", ({ node }) => {
      const notes = notesRef.current;
      const gNode = filteredData.nodes.find((n) => n.id === node);
      if (gNode?.file_path) {
        const note = notes.find((n) => n.file_path === gNode.file_path);
        if (note) {
          dispatch({ type: "SET_ACTIVE_NOTE", id: note.id });
          dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
        }
      }
    });

    renderer.on("enterNode", ({ node }) => {
      if (containerRef.current) containerRef.current.style.cursor = "pointer";
      const gNode = filteredData.nodes.find((n) => n.id === node);
      setHoveredNode(gNode?.label ?? null);

      // Dim non-connected nodes
      const neighbors = new Set<string>();
      neighbors.add(node);
      graph.forEachNeighbor(node, (neighbor) => neighbors.add(neighbor));

      graph.forEachNode((n) => {
        if (neighbors.has(n)) {
          graph.setNodeAttribute(n, "color", NODE_COLORS[filteredData.nodes.find((gn) => gn.id === n)?.node_type ?? "note"] || "#555");
        } else {
          graph.setNodeAttribute(n, "color", "rgba(80,80,80,0.3)");
        }
      });
      graph.forEachEdge((e, _attrs, source, target) => {
        if (neighbors.has(source) && neighbors.has(target)) {
          graph.setEdgeAttribute(e, "color", "rgba(255,255,255,0.3)");
        } else {
          graph.setEdgeAttribute(e, "color", "rgba(255,255,255,0.02)");
        }
      });
      renderer.refresh();
    });

    renderer.on("leaveNode", () => {
      if (containerRef.current) containerRef.current.style.cursor = "default";
      setHoveredNode(null);

      // Restore colors
      graph.forEachNode((n) => {
        const gNode = filteredData.nodes.find((gn) => gn.id === n);
        graph.setNodeAttribute(n, "color", NODE_COLORS[gNode?.node_type ?? "note"] || "#555");
      });
      graph.forEachEdge((e) => {
        const [source, target] = graph.extremities(e);
        const edgeData = filteredData.edges.find(
          (ed) => ed.source === source && ed.target === target
        );
        graph.setEdgeAttribute(
          e,
          "color",
          EDGE_COLORS[edgeData?.edge_type ?? ""] || "rgba(255,255,255,0.05)"
        );
      });
      renderer.refresh();
    });

    sigmaRef.current = renderer;
    return () => renderer.kill();
  }, [filteredData, dispatch]);

  const handleZoomIn = useCallback(() => {
    const camera = sigmaRef.current?.getCamera();
    if (camera) camera.animatedZoom({ duration: 200 });
  }, []);

  const handleZoomOut = useCallback(() => {
    const camera = sigmaRef.current?.getCamera();
    if (camera) camera.animatedUnzoom({ duration: 200 });
  }, []);

  const handleFitView = useCallback(() => {
    const camera = sigmaRef.current?.getCamera();
    if (camera) camera.animatedReset({ duration: 300 });
  }, []);

  const toggleFilter = useCallback((type: string) => {
    setActiveFilters((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  }, []);

  return (
    <div className="main-content">
      <div className="editor-header">
        <div className="editor-breadcrumb">
          <span>Knowledge Graph</span>
          {filteredData && (
            <span style={{ color: "var(--text-tertiary)", fontSize: 12 }}>
              &nbsp;· {filteredData.nodes.length} nodes ·{" "}
              {filteredData.edges.length} edges
            </span>
          )}
        </div>
        <div className="editor-actions">
          <button
            className={`icon-btn ${mode === "local" ? "active" : ""}`}
            onClick={() => setMode(mode === "global" ? "local" : "global")}
            title={mode === "global" ? "Local graph" : "Global graph"}
          >
            <Focus size={14} />
          </button>
          <button className="icon-btn" onClick={handleZoomIn} title="Zoom in">
            <ZoomIn size={14} />
          </button>
          <button className="icon-btn" onClick={handleZoomOut} title="Zoom out">
            <ZoomOut size={14} />
          </button>
          <button className="icon-btn" onClick={handleFitView} title="Fit view">
            <Maximize2 size={14} />
          </button>
          <button className="icon-btn" onClick={fetchGraph} title="Refresh">
            <RefreshCw
              size={14}
              className={loading ? "loading-spinner" : ""}
            />
          </button>
        </div>
      </div>

      <div style={{ flex: 1, position: "relative" }}>
        {loading && !graphData && (
          <div className="empty-state">
            <div className="loading-spinner" />
            <p>Loading graph...</p>
          </div>
        )}
        <div ref={containerRef} className="graph-container" />

        {/* Hover tooltip */}
        {hoveredNode && (
          <div className="graph-tooltip">{hoveredNode}</div>
        )}

        {/* Filter toggles */}
        <div className="graph-legend">
          {Object.entries(NODE_COLORS).map(([type, color]) => (
            <div
              key={type}
              className={`graph-legend-item ${
                activeFilters.has(type) ? "" : "dimmed"
              }`}
              onClick={() => toggleFilter(type)}
              style={{ cursor: "pointer" }}
            >
              <div
                className="graph-legend-dot"
                style={{
                  background: activeFilters.has(type) ? color : "#444",
                }}
              />
              <span style={{ textTransform: "capitalize" }}>{type}</span>
            </div>
          ))}
        </div>

        {/* Mode badge */}
        <div className="graph-mode-badge">
          <Layers size={11} />
          <span>{mode === "local" ? "Local" : "Global"}</span>
        </div>
      </div>
    </div>
  );
}
