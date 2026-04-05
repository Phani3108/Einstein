import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import Link from "@tiptap/extension-link";
import TaskList from "@tiptap/extension-task-list";
import TaskItem from "@tiptap/extension-task-item";
import Highlight from "@tiptap/extension-highlight";
import Typography from "@tiptap/extension-typography";
import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useApp } from "../lib/store";
import { api } from "../lib/api";
import { processNoteThroughPipeline } from "../lib/dataPipeline";
import { pluginRegistry } from "../lib/plugins";
import { marked } from "marked";
import {
  Bold,
  Italic,
  Code,
  List,
  ListOrdered,
  Quote,
  Heading1,
  Heading2,
  Heading3,
  Minus,
  CheckSquare,
  Highlighter,
  FileText,
  Brain,
  Loader,
  Undo2,
  Redo2,
  Copy,
  Clipboard,
  Share2,
  Paperclip,
  Link as LinkIcon,
  Image,
  Table,
  Strikethrough,
} from "lucide-react";

export function Editor() {
  const { state, dispatch } = useApp();
  const { activeNoteId, notes } = state;
  const activeNote = useMemo(
    () => notes.find((n) => n.id === activeNoteId),
    [notes, activeNoteId]
  );
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isSettingContent = useRef(false);
  const [saveStatus, setSaveStatus] = useState<"saved" | "saving" | "extracting">("saved");
  const [aiAvailable, setAiAvailable] = useState(false);

  // Check sidecar availability on mount
  useEffect(() => {
    api.sidecarHealth().then((h) => setAiAvailable(h?.status === "ok"));
  }, []);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3] },
        codeBlock: {
          HTMLAttributes: { class: "code-block" },
        },
      }),
      Placeholder.configure({
        placeholder: "Start writing... Use [[wikilinks]] to connect ideas.",
      }),
      Link.configure({
        openOnClick: false,
        HTMLAttributes: { class: "wikilink" },
      }),
      TaskList,
      TaskItem.configure({ nested: true }),
      Highlight.configure({ multicolor: true }),
      Typography,
    ],
    content: "",
    editorProps: {
      attributes: {
        class: "tiptap",
        spellcheck: "true",
      },
    },
    onUpdate: ({ editor: ed }) => {
      if (isSettingContent.current) return;
      if (saveTimer.current) clearTimeout(saveTimer.current);
      saveTimer.current = setTimeout(() => {
        autoSave(ed.getHTML());
      }, 1200);
    },
  });

  const autoSave = useCallback(
    async (html: string) => {
      if (!activeNote) return;
      const content = htmlToMarkdown(html);
      setSaveStatus("saving");
      try {
        // Use unified pipeline: save → extract entities → extract actions → persist → RAG index
        const result = await processNoteThroughPipeline(
          {
            ...activeNote,
            content,
          },
          dispatch,
          {
            skipAI: !aiAvailable,
            source: "editor",
          },
          (stage) => {
            switch (stage) {
              case "saving":
                setSaveStatus("saving");
                break;
              case "extracting-entities":
              case "extracting-actions":
                setSaveStatus("extracting");
                break;
              case "done":
                setSaveStatus("saved");
                break;
            }
          },
        );

        if (result.errors.length > 0) {
          console.warn("Pipeline completed with errors:", result.errors);
        }
        setSaveStatus("saved");
      } catch (err) {
        console.error("Auto-save failed:", err);
        setSaveStatus("saved");
      }
    },
    [activeNote, dispatch, aiAvailable]
  );

  // Load note into editor when selection changes
  useEffect(() => {
    if (!editor || !activeNote) return;
    isSettingContent.current = true;
    const html = markdownToHtml(activeNote.content);
    editor.commands.setContent(html);
    // small delay to let ProseMirror settle
    requestAnimationFrame(() => {
      isSettingContent.current = false;
    });
    // Fire plugin hooks
    pluginRegistry.emit("on_note_load", { note: activeNote });
  }, [activeNoteId, editor]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleManualSave = useCallback(() => {
    if (!editor) return;
    if (saveTimer.current) clearTimeout(saveTimer.current);
    autoSave(editor.getHTML());
  }, [editor, autoSave]);

  if (!activeNote) {
    return (
      <div className="main-content">
        <div className="empty-state">
          <FileText size={48} className="empty-icon" />
          <p>Select a note or create a new one</p>
          <p className="hint">
            <kbd>⌘P</kbd> search &nbsp; <kbd>⌘N</kbd> new note
          </p>
        </div>
      </div>
    );
  }

  const pathParts = activeNote.file_path.split("/");

  return (
    <div className="main-content">
      <div className="editor-header">
        <div className="editor-breadcrumb">
          {pathParts.map((part, i) => (
            <span key={i}>
              {i > 0 && <span className="sep">/</span>}
              <span>{part.replace(".md", "")}</span>
            </span>
          ))}
        </div>
        <div className="editor-actions">
          <button
            className="icon-btn"
            onClick={handleManualSave}
            title="Save (⌘S)"
          >
            <span style={{ fontSize: 11 }}>Save</span>
          </button>
        </div>
      </div>

      {editor && (
        <div className="toolbar">
          <ToolbarButton
            icon={<Bold size={14} />}
            active={editor.isActive("bold")}
            onClick={() => editor.chain().focus().toggleBold().run()}
            title="Bold (⌘B)"
          />
          <ToolbarButton
            icon={<Italic size={14} />}
            active={editor.isActive("italic")}
            onClick={() => editor.chain().focus().toggleItalic().run()}
            title="Italic (⌘I)"
          />
          <ToolbarButton
            icon={<Code size={14} />}
            active={editor.isActive("code")}
            onClick={() => editor.chain().focus().toggleCode().run()}
            title="Code"
          />
          <ToolbarButton
            icon={<Highlighter size={14} />}
            active={editor.isActive("highlight")}
            onClick={() => editor.chain().focus().toggleHighlight().run()}
            title="Highlight"
          />

          <div className="divider" />

          <ToolbarButton
            icon={<Heading1 size={14} />}
            active={editor.isActive("heading", { level: 1 })}
            onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
            title="Heading 1"
          />
          <ToolbarButton
            icon={<Heading2 size={14} />}
            active={editor.isActive("heading", { level: 2 })}
            onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
            title="Heading 2"
          />
          <ToolbarButton
            icon={<Heading3 size={14} />}
            active={editor.isActive("heading", { level: 3 })}
            onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
            title="Heading 3"
          />

          <div className="divider" />

          <ToolbarButton
            icon={<List size={14} />}
            active={editor.isActive("bulletList")}
            onClick={() => editor.chain().focus().toggleBulletList().run()}
            title="Bullet list"
          />
          <ToolbarButton
            icon={<ListOrdered size={14} />}
            active={editor.isActive("orderedList")}
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
            title="Ordered list"
          />
          <ToolbarButton
            icon={<CheckSquare size={14} />}
            active={editor.isActive("taskList")}
            onClick={() => editor.chain().focus().toggleTaskList().run()}
            title="Task list"
          />
          <ToolbarButton
            icon={<Quote size={14} />}
            active={editor.isActive("blockquote")}
            onClick={() => editor.chain().focus().toggleBlockquote().run()}
            title="Quote"
          />
          <ToolbarButton
            icon={<Minus size={14} />}
            active={false}
            onClick={() => editor.chain().focus().setHorizontalRule().run()}
            title="Divider"
          />
          <ToolbarButton
            icon={<Strikethrough size={14} />}
            active={editor.isActive("strike")}
            onClick={() => editor.chain().focus().toggleStrike().run()}
            title="Strikethrough"
          />

          <div className="divider" />

          <ToolbarButton
            icon={<Undo2 size={14} />}
            active={false}
            onClick={() => editor.chain().focus().undo().run()}
            title="Undo (⌘Z)"
          />
          <ToolbarButton
            icon={<Redo2 size={14} />}
            active={false}
            onClick={() => editor.chain().focus().redo().run()}
            title="Redo (⌘⇧Z)"
          />

          <div className="divider" />

          <ToolbarButton
            icon={<Copy size={14} />}
            active={false}
            onClick={() => {
              const sel = window.getSelection()?.toString();
              if (sel) navigator.clipboard.writeText(sel);
            }}
            title="Copy selection"
          />
          <ToolbarButton
            icon={<Clipboard size={14} />}
            active={false}
            onClick={async () => {
              try {
                const text = await navigator.clipboard.readText();
                if (text) editor.chain().focus().insertContent(text).run();
              } catch { /* clipboard denied */ }
            }}
            title="Paste from clipboard"
          />

          <div className="divider" />

          <ToolbarButton
            icon={<LinkIcon size={14} />}
            active={editor.isActive("link")}
            onClick={() => {
              if (editor.isActive("link")) {
                editor.chain().focus().unsetLink().run();
              } else {
                const url = window.prompt("Enter URL:");
                if (url) editor.chain().focus().setLink({ href: url }).run();
              }
            }}
            title="Insert link"
          />
          <ToolbarButton
            icon={<Image size={14} />}
            active={false}
            onClick={() => {
              const url = window.prompt("Image URL:");
              if (url) {
                editor.chain().focus().insertContent(
                  `<img src="${url}" alt="image" />`
                ).run();
              }
            }}
            title="Insert image"
          />
          <ToolbarButton
            icon={<Paperclip size={14} />}
            active={false}
            onClick={() => {
              // Trigger hidden file input
              const input = document.createElement("input");
              input.type = "file";
              input.onchange = () => {
                const file = input.files?.[0];
                if (file) {
                  const reader = new FileReader();
                  reader.onload = () => {
                    const dataUrl = reader.result as string;
                    if (file.type.startsWith("image/")) {
                      editor.chain().focus().insertContent(
                        `<img src="${dataUrl}" alt="${file.name}" />`
                      ).run();
                    } else {
                      editor.chain().focus().insertContent(
                        `[${file.name}](attachment:${file.name})`
                      ).run();
                    }
                  };
                  reader.readAsDataURL(file);
                }
              };
              input.click();
            }}
            title="Attach file"
          />
          <ToolbarButton
            icon={<Share2 size={14} />}
            active={false}
            onClick={() => {
              if (!activeNote) return;
              const text = activeNote.content;
              if (navigator.share) {
                navigator.share({ title: activeNote.title, text }).catch(() => {});
              } else {
                navigator.clipboard.writeText(text);
                // Visual feedback handled by status bar
              }
            }}
            title="Share / Copy note"
          />
        </div>
      )}

      <div className="editor-container">
        <div className="editor-wrapper">
          <EditorContent editor={editor} />
        </div>
      </div>

      <div className="status-bar">
        <div className="status-item">
          {saveStatus === "saving" ? (
            <Loader size={10} className="loading-spinner" />
          ) : saveStatus === "extracting" ? (
            <Brain size={10} className="loading-spinner" />
          ) : (
            <div className="dot" />
          )}
          <span>
            {saveStatus === "saving"
              ? "Saving..."
              : saveStatus === "extracting"
              ? "Extracting entities..."
              : "Saved"}
          </span>
        </div>
        <div className="status-item">
          <span>
            {activeNote.content.split(/\s+/).filter(Boolean).length} words
          </span>
        </div>
        {aiAvailable && (
          <div className="status-item" title="AI sidecar connected">
            <Brain size={10} />
            <span>AI</span>
          </div>
        )}
      </div>
    </div>
  );
}

function ToolbarButton({
  icon,
  active,
  onClick,
  title,
}: {
  icon: React.ReactNode;
  active: boolean;
  onClick: () => void;
  title: string;
}) {
  return (
    <button
      className={`icon-btn ${active ? "active" : ""}`}
      onClick={onClick}
      title={title}
    >
      {icon}
    </button>
  );
}

/* ================================================================
   Markdown <-> HTML conversion
   Using the `marked` library for reliable parsing
   ================================================================ */

function markdownToHtml(md: string): string {
  if (!md || !md.trim()) return "<p></p>";

  let processed = md;

  // Pre-process callouts: > [!type] text
  processed = processed.replace(
    /^> \[!(\w+)\]\s*(.*?)$\n((?:^>.*$\n?)*)/gm,
    (_match, type, title, body) => {
      const cleanBody = body.replace(/^> ?/gm, "").trim();
      const icons: Record<string, string> = {
        note: "\u{1F4DD}", info: "\u2139\uFE0F", tip: "\u{1F4A1}", warning: "\u26A0\uFE0F",
        danger: "\u{1F534}", important: "\u2757", caution: "\u26A1", example: "\u{1F4CB}",
        quote: "\u{1F4AC}", abstract: "\u{1F4C4}", todo: "\u2611\uFE0F", success: "\u2705",
        question: "\u2753", failure: "\u274C", bug: "\u{1F41B}",
      };
      const icon = icons[type.toLowerCase()] || "\u{1F4CC}";
      return `<div class="callout callout-${type.toLowerCase()}"><div class="callout-title">${icon} ${title || type}</div><div class="callout-content">${cleanBody}</div></div>\n`;
    }
  );

  // Pre-process inline tags: #tag -> styled spans
  processed = processed.replace(
    /(?:^|\s)#([a-zA-Z][a-zA-Z0-9_-]*)/g,
    (match, tag) => {
      const prefix = match.startsWith(" ") ? " " : "";
      return `${prefix}<span class="inline-tag" data-tag="${tag}">#${tag}</span>`;
    }
  );

  // Pre-process wikilinks: [[target]] -> <a> tags
  processed = processed.replace(
    /\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]/g,
    (_match, target, display) =>
      `<a class="wikilink" href="#" data-link="${target}">${display || target}</a>`
  );

  // Use marked for standard markdown
  const html = marked.parse(processed, { async: false, gfm: true, breaks: true });
  return typeof html === "string" ? html : "";
}

function htmlToMarkdown(html: string): string {
  const doc = new DOMParser().parseFromString(html, "text/html");
  return nodeToMarkdown(doc.body).trim();
}

function nodeToMarkdown(node: Node): string {
  if (node.nodeType === Node.TEXT_NODE) {
    return node.textContent || "";
  }

  if (node.nodeType !== Node.ELEMENT_NODE) return "";
  const el = node as HTMLElement;
  const tag = el.tagName.toLowerCase();
  const children = Array.from(el.childNodes).map(nodeToMarkdown).join("");

  switch (tag) {
    case "h1":
      return `# ${children}\n\n`;
    case "h2":
      return `## ${children}\n\n`;
    case "h3":
      return `### ${children}\n\n`;
    case "p":
      return `${children}\n\n`;
    case "strong":
    case "b":
      return `**${children}**`;
    case "em":
    case "i":
      return `*${children}*`;
    case "code":
      if (el.parentElement?.tagName.toLowerCase() === "pre") return children;
      return `\`${children}\``;
    case "pre":
      return `\`\`\`\n${children}\n\`\`\`\n\n`;
    case "blockquote":
      return children
        .split("\n")
        .map((line) => `> ${line}`)
        .join("\n") + "\n\n";
    case "ul":
      return children;
    case "ol":
      return children;
    case "li": {
      const parent = el.parentElement?.tagName.toLowerCase();
      const prefix = parent === "ol" ? "1. " : "- ";
      const checkbox = el.querySelector('input[type="checkbox"]');
      if (checkbox) {
        const checked = (checkbox as HTMLInputElement).checked;
        return `- [${checked ? "x" : " "}] ${children.replace(/^\s*/, "")}\n`;
      }
      return `${prefix}${children.trim()}\n`;
    }
    case "a": {
      const link = el.getAttribute("data-link");
      if (link || el.classList.contains("wikilink")) {
        return `[[${link || children}]]`;
      }
      const href = el.getAttribute("href") || "";
      return `[${children}](${href})`;
    }
    case "hr":
      return `---\n\n`;
    case "br":
      return "\n";
    case "mark":
      return `==${children}==`;
    case "img": {
      const src = el.getAttribute("src") || "";
      const alt = el.getAttribute("alt") || "";
      return `![${alt}](${src})`;
    }
    case "div": {
      if (el.classList.contains("callout")) {
        const type = Array.from(el.classList).find(c => c.startsWith("callout-"))?.replace("callout-", "") || "note";
        const titleEl = el.querySelector(".callout-title");
        const contentEl = el.querySelector(".callout-content");
        const title = titleEl?.textContent?.replace(/^[^\w]*/, "").trim() || "";
        const content = contentEl?.textContent?.trim() || "";
        return `> [!${type}] ${title}\n> ${content}\n\n`;
      }
      return children;
    }
    case "span": {
      if (el.classList.contains("inline-tag")) {
        return `#${el.getAttribute("data-tag") || children.replace("#", "")}`;
      }
      return children;
    }
    default:
      return children;
  }
}
