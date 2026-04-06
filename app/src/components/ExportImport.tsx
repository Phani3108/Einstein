import { useState, useCallback } from "react";
import { useApp } from "../lib/store";
import { api } from "../lib/api";
import { processNoteThroughPipeline } from "../lib/dataPipeline";
import {
  Download,
  Upload,
  FileText,
  FileJson,
  Globe,
  CheckCircle,
  Loader,
  FilePlus,
} from "lucide-react";

type ExportFormat = "markdown" | "json" | "html";

export function ExportImport() {
  const { state, dispatch } = useApp();
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importingDoc, setImportingDoc] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  // ---------------------------------------------------------------------------
  // Export
  // ---------------------------------------------------------------------------

  const handleExport = useCallback(
    async (format: ExportFormat) => {
      setExporting(true);
      setResult(null);
      try {
        const notes = state.notes;
        let content = "";
        let filename = "";
        let mimeType = "";

        switch (format) {
          case "markdown": {
            content = notes
              .map((n) => {
                const fm = Object.entries(n.frontmatter)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join("\n");
                const header = fm ? `---\n${fm}\n---\n\n` : "";
                return `${header}${n.content}\n\n---\n<!-- file: ${n.file_path} -->\n`;
              })
              .join("\n");
            filename = "einstein-export.md";
            mimeType = "text/markdown";
            break;
          }
          case "json": {
            const data = notes.map((n) => ({
              id: n.id,
              title: n.title,
              file_path: n.file_path,
              content: n.content,
              frontmatter: n.frontmatter,
              outgoing_links: n.outgoing_links,
              created_at: n.created_at,
              updated_at: n.updated_at,
            }));
            content = JSON.stringify({ version: "1.0", notes: data }, null, 2);
            filename = "einstein-export.json";
            mimeType = "application/json";
            break;
          }
          case "html": {
            const noteHtml = notes
              .map(
                (n) =>
                  `<article><h2>${escapeHtml(n.title)}</h2><pre>${escapeHtml(n.content)}</pre></article>`
              )
              .join("\n");
            content = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Einstein Export</title>
  <style>
    body { font-family: -apple-system, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #111; color: #eee; }
    article { border-bottom: 1px solid #333; padding: 20px 0; }
    h2 { color: #6ea8fe; }
    pre { white-space: pre-wrap; font-size: 14px; line-height: 1.6; }
  </style>
</head>
<body>
  <h1>Einstein Notes Export</h1>
  <p>${notes.length} notes exported on ${new Date().toLocaleDateString()}</p>
  ${noteHtml}
</body>
</html>`;
            filename = "einstein-export.html";
            mimeType = "text/html";
            break;
          }
        }

        // Trigger browser download
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);

        setResult(`Exported ${notes.length} notes as ${format.toUpperCase()}`);
      } catch (err) {
        setResult(`Export failed: ${err}`);
      } finally {
        setExporting(false);
      }
    },
    [state.notes]
  );

  // ---------------------------------------------------------------------------
  // Import
  // ---------------------------------------------------------------------------

  const handleImportJSON = useCallback(async () => {
    setImporting(true);
    setResult(null);
    try {
      const input = document.createElement("input");
      input.type = "file";
      input.accept = ".json";

      input.onchange = async () => {
        const file = input.files?.[0];
        if (!file) return;

        const text = await file.text();
        const data = JSON.parse(text);
        const notes = data.notes ?? data;

        let imported = 0;
        for (const n of notes) {
          if (n.file_path && n.content) {
            try {
              const note = await api.saveNote(
                n.file_path,
                n.title || n.file_path.replace(".md", ""),
                n.content,
                n.frontmatter || {}
              );
              dispatch({ type: "UPDATE_NOTE", note });
              imported++;
            } catch {
              // Skip failed notes
            }
          }
        }

        setResult(`Imported ${imported} notes`);
        setImporting(false);
      };

      input.click();
    } catch (err) {
      setResult(`Import failed: ${err}`);
      setImporting(false);
    }
  }, [dispatch]);

  const handleImportDocument = useCallback(async (file: File) => {
    setImportingDoc(true);
    setResult(null);
    try {
      const name = file.name;
      const ext = name.split(".").pop()?.toLowerCase() ?? "";

      if (!["txt", "md", "json"].includes(ext)) {
        setResult("Unsupported file type. Please upload .txt, .md, or .json files.");
        setImportingDoc(false);
        return;
      }

      const text = await file.text();

      // If JSON, delegate to the existing JSON import flow
      if (ext === "json") {
        try {
          const data = JSON.parse(text);
          const notes = data.notes ?? data;
          let imported = 0;
          for (const n of notes) {
            if (n.file_path && n.content) {
              try {
                const note = await api.saveNote(
                  n.file_path,
                  n.title || n.file_path.replace(".md", ""),
                  n.content,
                  n.frontmatter || {},
                );
                dispatch({ type: "UPDATE_NOTE", note });
                imported++;
              } catch {
                // Skip failed notes
              }
            }
          }
          setResult(`Imported ${imported} notes from JSON`);
        } catch {
          setResult("Invalid JSON file format");
        }
        setImportingDoc(false);
        return;
      }

      // For .txt / .md: create a single note from the file content
      const titleFromName = name.replace(/\.[^.]+$/, "");
      const slug = titleFromName
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "");
      const filePath = `imported/${slug}.md`;

      const note = await api.saveNote(filePath, titleFromName, text, {
        type: "document",
        source: "file-upload",
        original_filename: name,
      });

      dispatch({ type: "UPDATE_NOTE", note });

      // Run through pipeline for entity extraction
      processNoteThroughPipeline(note, dispatch, {
        alreadySaved: true,
        source: "document-upload",
      }).catch((err) => console.error("Pipeline failed for imported document:", err));

      setResult(`Imported "${titleFromName}" as a new note`);
    } catch (err) {
      setResult(`Document import failed: ${err}`);
    } finally {
      setImportingDoc(false);
    }
  }, [dispatch]);

  const handleDocDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleImportDocument(file);
  }, [handleImportDocument]);

  const handleDocBrowse = useCallback(() => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".txt,.md,.json";
    input.onchange = () => {
      const file = input.files?.[0];
      if (file) handleImportDocument(file);
    };
    input.click();
  }, [handleImportDocument]);

  const handleImportExternal = useCallback(async () => {
    setResult(
      "To import from another tool: just point Einstein to the folder containing your .md files. " +
      "Einstein reads Markdown files natively — no conversion needed!"
    );
  }, []);

  return (
    <div className="main-content">
      <div className="editor-header">
        <div className="editor-breadcrumb">
          <span>Export & Import</span>
        </div>
      </div>

      <div className="export-import-wrapper">
        {/* Export Section */}
        <div className="export-section">
          <h3>
            <Download size={16} /> Export Notes
          </h3>
          <p className="section-desc">
            Export all {state.notes.length} notes from your vault
          </p>

          <div className="export-buttons">
            <button
              className="export-btn"
              onClick={() => handleExport("markdown")}
              disabled={exporting}
            >
              <FileText size={20} />
              <span className="export-btn-label">Markdown</span>
              <span className="export-btn-desc">Single .md file</span>
            </button>

            <button
              className="export-btn"
              onClick={() => handleExport("json")}
              disabled={exporting}
            >
              <FileJson size={20} />
              <span className="export-btn-label">JSON</span>
              <span className="export-btn-desc">Structured data</span>
            </button>

            <button
              className="export-btn"
              onClick={() => handleExport("html")}
              disabled={exporting}
            >
              <Globe size={20} />
              <span className="export-btn-label">HTML</span>
              <span className="export-btn-desc">Web-ready page</span>
            </button>
          </div>
        </div>

        {/* Import Section */}
        <div className="export-section">
          <h3>
            <Upload size={16} /> Import Notes
          </h3>
          <p className="section-desc">
            Import notes from other tools
          </p>

          <div className="export-buttons">
            <button
              className="export-btn"
              onClick={handleImportJSON}
              disabled={importing}
            >
              {importing ? <Loader size={20} className="loading-spinner" /> : <FileJson size={20} />}
              <span className="export-btn-label">JSON File</span>
              <span className="export-btn-desc">Einstein/custom export</span>
            </button>

            <button className="export-btn" onClick={handleImportExternal}>
              <FileText size={20} />
              <span className="export-btn-label">Markdown Vault</span>
              <span className="export-btn-desc">Open vault directly</span>
            </button>
          </div>
        </div>

        {/* Import Document Section */}
        <div className="export-section">
          <h3>
            <FilePlus size={16} /> Import Document
          </h3>
          <p className="section-desc">
            Upload a text or Markdown file to create a new note
          </p>

          <div
            className={`ei-dropzone${dragOver ? " ei-dragover" : ""}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDocDrop}
            onClick={handleDocBrowse}
          >
            {importingDoc ? (
              <>
                <Loader size={24} className="loading-spinner" />
                <span>Importing...</span>
              </>
            ) : (
              <>
                <Upload size={24} />
                <span>Drop a file here or click to browse</span>
                <span style={{ fontSize: 11, opacity: 0.6 }}>
                  Supports .txt, .md, .json
                </span>
              </>
            )}
          </div>
        </div>

        {/* Result */}
        {result && (
          <div className="export-result">
            <CheckCircle size={14} />
            <span>{result}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
