import { useState } from "react";
import {
  Book,
  Code,
  Keyboard,
  Lightbulb,
  Puzzle,
  Terminal,
  Rocket,
  Zap,
  BookOpen,
  FileCode,
  Command,
  ChevronDown,
  ChevronRight,
  Copy,
  Check,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Collapsible Section                                                */
/* ------------------------------------------------------------------ */

function Section({
  icon,
  title,
  defaultOpen = false,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="devhub-section">
      <button
        className="devhub-section-header"
        onClick={() => setOpen((o) => !o)}
      >
        <span className="devhub-section-icon">{icon}</span>
        <span className="devhub-section-title">{title}</span>
        {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </button>
      {open && <div className="devhub-section-body">{children}</div>}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Code Block with copy button                                        */
/* ------------------------------------------------------------------ */

function CodeBlock({ code, lang = "" }: { code: string; lang?: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  return (
    <div className="devhub-codeblock">
      {lang && <span className="devhub-codeblock-lang">{lang}</span>}
      <button className="devhub-codeblock-copy" onClick={handleCopy} title="Copy">
        {copied ? <Check size={13} /> : <Copy size={13} />}
      </button>
      <pre>
        <code>{code}</code>
      </pre>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Keyboard Shortcut Badge                                            */
/* ------------------------------------------------------------------ */

function Shortcut({ keys, label }: { keys: string; label: string }) {
  return (
    <div className="devhub-shortcut">
      <kbd>{keys}</kbd>
      <span>{label}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main DevHub Component                                              */
/* ------------------------------------------------------------------ */

export function DevHub() {
  return (
    <div className="main-content" style={{ overflow: "auto" }}>
      {/* Header */}
      <div className="editor-header">
        <div className="editor-breadcrumb">
          <BookOpen size={14} style={{ marginRight: 6 }} />
          <span>Developer Hub</span>
        </div>
      </div>

      <div className="devhub-wrapper">
        <div className="devhub-hero">
          <Rocket size={32} />
          <h1>Einstein Developer Hub</h1>
          <p>
            Everything you need to master Einstein and build on top of it.
          </p>
        </div>

        {/* -------------------------------------------------------- */}
        {/*  1. Getting Started                                       */}
        {/* -------------------------------------------------------- */}
        <Section icon={<Book size={18} />} title="Getting Started" defaultOpen>
          <p>
            <strong>Einstein</strong> is an AI-powered second brain for knowledge
            management. It lets you capture, connect, and retrieve ideas using a
            local-first architecture that keeps your data entirely on your device.
          </p>

          <h4>How Einstein is different</h4>
          <ul>
            <li>
              <strong>Local-first AI</strong> &mdash; your notes never leave your
              machine. The AI sidecar runs locally for entity extraction, search,
              and summarization.
            </li>
            <li>
              <strong>MCP &amp; A2A protocol support</strong> &mdash; expose your
              knowledge base to any AI agent via the Model Context Protocol or
              Agent-to-Agent protocol.
            </li>
            <li>
              <strong>Developer SDK</strong> &mdash; a Python SDK and REST API so
              you can script, automate, and build on top of your vault.
            </li>
            <li>
              <strong>Knowledge Graph</strong> &mdash; automatic entity extraction
              and a visual graph view that reveals hidden connections between your
              notes.
            </li>
          </ul>
        </Section>

        {/* -------------------------------------------------------- */}
        {/*  2. Keyboard Shortcuts                                    */}
        {/* -------------------------------------------------------- */}
        <Section icon={<Keyboard size={18} />} title="Keyboard Shortcuts">
          <div className="devhub-shortcuts-grid">
            <Shortcut keys="⌘ N" label="New Note" />
            <Shortcut keys="⌘ P" label="Quick Search" />
            <Shortcut keys="⌘ S" label="Save Note" />
            <Shortcut keys="⌘ \" label="Toggle Sidebar" />
            <Shortcut keys="⌘ B" label="Bold" />
            <Shortcut keys="⌘ I" label="Italic" />
            <Shortcut keys="⌘ K" label="Insert Link" />
            <Shortcut keys="⌘ ⇧ H" label="Highlight" />
            <Shortcut keys="⌘ ↵" label="Save & Extract Entities" />
          </div>
        </Section>

        {/* -------------------------------------------------------- */}
        {/*  3. Templates Guide                                       */}
        {/* -------------------------------------------------------- */}
        <Section icon={<FileCode size={18} />} title="Templates Guide">
          <p>
            Templates let you scaffold notes instantly. Einstein looks for
            Markdown files inside a <code>templates/</code> folder in your vault.
          </p>

          <h4>Setup</h4>
          <ol>
            <li>
              Create a <code>templates/</code> directory at the root of your
              vault.
            </li>
            <li>
              Add <code>.md</code> files with your template content.
            </li>
            <li>
              Use variables that Einstein will replace automatically.
            </li>
          </ol>

          <h4>Available Variables</h4>
          <CodeBlock
            lang="markdown"
            code={`{{date:YYYY-MM-DD}}   — formatted date
{{time:HH:mm}}        — formatted time
{{title}}             — note title
{{date}}              — today's date (default format)
{{day}}               — day of the week`}
          />

          <h4>Example: Meeting Template</h4>
          <CodeBlock
            lang="markdown"
            code={`---
type: meeting
date: {{date:YYYY-MM-DD}}
---

# {{title}}

## Attendees
-

## Agenda
1.

## Notes


## Action Items
- [ ] `}
          />

          <p>
            <strong>Tip:</strong> Templates whose filename starts with{" "}
            <code>daily</code> are automatically applied when you create a daily
            note.
          </p>
        </Section>

        {/* -------------------------------------------------------- */}
        {/*  4. Markdown Tips                                         */}
        {/* -------------------------------------------------------- */}
        <Section icon={<Code size={18} />} title="Markdown Tips">
          <h4>Headings</h4>
          <CodeBlock
            lang="markdown"
            code={`# Heading 1
## Heading 2
### Heading 3`}
          />

          <h4>Inline Formatting</h4>
          <CodeBlock
            lang="markdown"
            code={`**Bold text**
*Italic text*
\`inline code\`
~~Strikethrough~~`}
          />

          <h4>Wikilinks &amp; Tags</h4>
          <CodeBlock
            lang="markdown"
            code={`[[Another Note]]      — link to a note (creates backlink)
[[Note|Display Text]] — aliased link
#tag                  — categorize with tags`}
          />

          <h4>Task Lists</h4>
          <CodeBlock
            lang="markdown"
            code={`- [ ] Incomplete task
- [x] Completed task`}
          />

          <h4>Callout Blocks</h4>
          <CodeBlock
            lang="markdown"
            code={`> [!info] Information
> Useful context for the reader.

> [!warning] Caution
> Something to watch out for.

> [!tip] Pro Tip
> A helpful suggestion.`}
          />

          <h4>Code Blocks</h4>
          <CodeBlock
            lang="markdown"
            code={`\`\`\`python
def hello():
    print("Hello from Einstein!")
\`\`\``}
          />
        </Section>

        {/* -------------------------------------------------------- */}
        {/*  5. Building with Einstein                                */}
        {/* -------------------------------------------------------- */}
        <Section icon={<Terminal size={18} />} title="Building with Einstein">
          <p>
            Einstein is designed to be extended. Here are the integration points
            available to developers.
          </p>

          {/* MCP Server */}
          <h4>
            <Puzzle size={14} style={{ marginRight: 4, verticalAlign: "middle" }} />
            MCP Server
          </h4>
          <p>
            Einstein exposes a <strong>Model Context Protocol</strong> server
            on <code>localhost:9721</code>. Any MCP-compatible AI agent can
            read, search, and create notes in your vault.
          </p>
          <CodeBlock
            lang="json"
            code={`{
  "mcpServers": {
    "einstein": {
      "url": "http://localhost:9721/mcp",
      "transport": "streamable-http"
    }
  }
}`}
          />

          {/* A2A Protocol */}
          <h4>
            <Zap size={14} style={{ marginRight: 4, verticalAlign: "middle" }} />
            A2A Protocol
          </h4>
          <p>
            The Agent-to-Agent protocol lets multiple AI agents collaborate
            through your Einstein vault. One agent can store findings while
            another retrieves and reasons over them.
          </p>
          <CodeBlock
            lang="python"
            code={`# A2A agent card discovery
import httpx

card = httpx.get("http://localhost:9721/.well-known/agent.json").json()
print(card["name"])        # "Einstein Knowledge Agent"
print(card["capabilities"]) # ["search", "create", "graph"]`}
          />

          {/* Python SDK */}
          <h4>
            <Command size={14} style={{ marginRight: 4, verticalAlign: "middle" }} />
            Python SDK
          </h4>
          <p>
            The SDK supports two modes: <strong>direct SQLite</strong> access
            (fastest, same machine) and <strong>HTTP</strong> mode (remote or
            multi-process).
          </p>
          <CodeBlock
            lang="python"
            code={`from einstein_sdk import EinsteinClient

# Direct mode — reads the SQLite vault directly
client = EinsteinClient(vault_path="~/Documents/MyVault")

# HTTP mode — talks to the running Einstein instance
client = EinsteinClient(base_url="http://localhost:9721")

# List all notes
notes = client.list_notes()

# Search
results = client.search("machine learning", limit=10)

# Create a note
client.create_note(
    title="SDK Test",
    content="Created via the Python SDK!",
    tags=["automated", "test"],
)`}
          />

          {/* REST API */}
          <h4>
            <Code size={14} style={{ marginRight: 4, verticalAlign: "middle" }} />
            REST API
          </h4>
          <CodeBlock
            lang="bash"
            code={`# List notes
curl http://localhost:9721/api/notes

# Get a single note
curl http://localhost:9721/api/notes/:id

# Create a note
curl -X POST http://localhost:9721/api/notes \\
  -H "Content-Type: application/json" \\
  -d '{"title":"Hello","content":"World","tags":["api"]}'

# Search
curl "http://localhost:9721/api/search?q=machine+learning&limit=5"

# Get knowledge graph
curl http://localhost:9721/api/graph`}
          />
        </Section>

        {/* -------------------------------------------------------- */}
        {/*  6. What You Can Build                                    */}
        {/* -------------------------------------------------------- */}
        <Section icon={<Lightbulb size={18} />} title="What You Can Build">
          <div className="devhub-ideas-grid">
            <div className="devhub-idea-card">
              <Rocket size={20} />
              <h5>Personal Knowledge Assistant</h5>
              <p>
                Wire Einstein to an LLM so it answers questions grounded in your
                own notes, not the open web.
              </p>
            </div>

            <div className="devhub-idea-card">
              <BookOpen size={20} />
              <h5>Automated Journaling Pipeline</h5>
              <p>
                Pull data from calendars, health apps, or git logs and generate
                a daily note automatically.
              </p>
            </div>

            <div className="devhub-idea-card">
              <Zap size={20} />
              <h5>Meeting Notes &rarr; Action Items</h5>
              <p>
                Feed meeting transcripts into Einstein and extract tasks,
                decisions, and follow-ups.
              </p>
            </div>

            <div className="devhub-idea-card">
              <Book size={20} />
              <h5>Research Paper Organizer</h5>
              <p>
                Import papers, auto-extract entities, and visualize the
                citation graph alongside your annotations.
              </p>
            </div>

            <div className="devhub-idea-card">
              <Puzzle size={20} />
              <h5>Project Standups</h5>
              <p>
                Template-driven daily standups that aggregate yesterday's notes,
                today's calendar, and open tasks.
              </p>
            </div>

            <div className="devhub-idea-card">
              <Terminal size={20} />
              <h5>Context-Aware AI Agent</h5>
              <p>
                Build an AI agent that uses MCP to read your vault and provide
                answers with full personal context.
              </p>
            </div>
          </div>
        </Section>

        {/* -------------------------------------------------------- */}
        {/*  7. Tips & Tricks                                         */}
        {/* -------------------------------------------------------- */}
        <Section icon={<Zap size={18} />} title="Tips & Tricks">
          <ul className="devhub-tips-list">
            <li>
              <strong>Build a journaling habit</strong> &mdash; use daily notes.
              Even a single sentence per day compounds into a rich personal log
              over months.
            </li>
            <li>
              <strong>Link everything</strong> &mdash; the graph view reveals
              hidden connections. When in doubt, add a{" "}
              <code>[[wikilink]]</code>.
            </li>
            <li>
              <strong>Use frontmatter</strong> &mdash; add YAML metadata at the
              top of notes (<code>type</code>, <code>status</code>,{" "}
              <code>project</code>) for powerful filtering.
            </li>
            <li>
              <strong>Bookmark important notes</strong> &mdash; starred notes
              appear in the sidebar for one-click access.
            </li>
            <li>
              <strong>AI Entity Extraction</strong> &mdash; after saving, hit{" "}
              <kbd>⌘ ↵</kbd> to let the AI sidecar pull out people, concepts,
              and dates automatically.
            </li>
            <li>
              <strong>Keyboard-first workflow</strong> &mdash; learn the
              shortcuts above and you can navigate, create, and format without
              touching the mouse.
            </li>
            <li>
              <strong>Use tags strategically</strong> &mdash; combine tags with
              wikilinks: tags for broad categories, links for specific
              relationships.
            </li>
          </ul>
        </Section>

        <div className="devhub-footer">
          <p>
            Built with care. Open an issue or submit a PR if you have ideas.
          </p>
        </div>
      </div>

      {/* Scoped styles */}
      <style>{`
        .devhub-wrapper {
          max-width: 780px;
          margin: 0 auto;
          padding: 24px 32px 64px;
          overflow-y: auto;
          height: 100%;
        }

        /* Hero */
        .devhub-hero {
          text-align: center;
          margin-bottom: 36px;
          padding: 32px 0 24px;
        }
        .devhub-hero h1 {
          font-size: 1.8rem;
          font-weight: 700;
          margin: 12px 0 6px;
          color: var(--text-primary, #e4e4e7);
        }
        .devhub-hero p {
          color: var(--text-muted, #a1a1aa);
          font-size: 0.95rem;
        }
        .devhub-hero svg {
          color: var(--accent, #3b82f6);
        }

        /* Section */
        .devhub-section {
          border: 1px solid var(--border, #27272a);
          border-radius: 10px;
          margin-bottom: 12px;
          background: var(--bg-secondary, #18181b);
          overflow: hidden;
        }
        .devhub-section-header {
          display: flex;
          align-items: center;
          gap: 10px;
          width: 100%;
          padding: 14px 18px;
          background: none;
          border: none;
          color: var(--text-primary, #e4e4e7);
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
          text-align: left;
        }
        .devhub-section-header:hover {
          background: var(--bg-hover, #27272a);
        }
        .devhub-section-header svg:last-child {
          margin-left: auto;
          color: var(--text-muted, #a1a1aa);
        }
        .devhub-section-icon {
          display: flex;
          color: var(--accent, #3b82f6);
        }
        .devhub-section-title {
          flex: 1;
        }
        .devhub-section-body {
          padding: 4px 20px 20px;
          color: var(--text-secondary, #d4d4d8);
          font-size: 0.9rem;
          line-height: 1.65;
        }
        .devhub-section-body h4 {
          margin: 18px 0 8px;
          font-size: 0.92rem;
          font-weight: 600;
          color: var(--text-primary, #e4e4e7);
          display: flex;
          align-items: center;
        }
        .devhub-section-body ul,
        .devhub-section-body ol {
          padding-left: 20px;
          margin: 8px 0;
        }
        .devhub-section-body li {
          margin-bottom: 6px;
        }
        .devhub-section-body code {
          background: var(--bg-tertiary, #27272a);
          padding: 1px 6px;
          border-radius: 4px;
          font-size: 0.85em;
          color: var(--accent, #3b82f6);
        }
        .devhub-section-body kbd {
          background: var(--bg-tertiary, #27272a);
          border: 1px solid var(--border, #3f3f46);
          padding: 2px 7px;
          border-radius: 4px;
          font-size: 0.82em;
          font-family: inherit;
        }
        .devhub-section-body p {
          margin: 8px 0;
        }

        /* Code block */
        .devhub-codeblock {
          position: relative;
          background: var(--bg-tertiary, #0f0f12);
          border: 1px solid var(--border, #27272a);
          border-radius: 8px;
          margin: 10px 0;
          overflow: hidden;
        }
        .devhub-codeblock pre {
          margin: 0;
          padding: 14px 16px;
          overflow-x: auto;
          font-size: 0.82rem;
          line-height: 1.6;
        }
        .devhub-codeblock code {
          background: none !important;
          padding: 0 !important;
          color: var(--text-secondary, #d4d4d8) !important;
          font-family: "SF Mono", "Fira Code", "Cascadia Code", monospace;
        }
        .devhub-codeblock-lang {
          position: absolute;
          top: 6px;
          right: 36px;
          font-size: 0.7rem;
          color: var(--text-muted, #71717a);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .devhub-codeblock-copy {
          position: absolute;
          top: 6px;
          right: 8px;
          background: none;
          border: none;
          color: var(--text-muted, #71717a);
          cursor: pointer;
          padding: 2px;
          display: flex;
          border-radius: 4px;
        }
        .devhub-codeblock-copy:hover {
          color: var(--text-primary, #e4e4e7);
          background: var(--bg-hover, #27272a);
        }

        /* Shortcuts grid */
        .devhub-shortcuts-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 8px;
        }
        .devhub-shortcut {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px 14px;
          background: var(--bg-tertiary, #0f0f12);
          border: 1px solid var(--border, #27272a);
          border-radius: 8px;
        }
        .devhub-shortcut kbd {
          background: var(--bg-secondary, #18181b);
          border: 1px solid var(--border, #3f3f46);
          padding: 3px 8px;
          border-radius: 5px;
          font-size: 0.8rem;
          font-family: inherit;
          white-space: nowrap;
          min-width: 50px;
          text-align: center;
        }
        .devhub-shortcut span {
          color: var(--text-secondary, #d4d4d8);
          font-size: 0.85rem;
        }

        /* Ideas grid */
        .devhub-ideas-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
          gap: 12px;
          margin-top: 8px;
        }
        .devhub-idea-card {
          padding: 16px;
          background: var(--bg-tertiary, #0f0f12);
          border: 1px solid var(--border, #27272a);
          border-radius: 10px;
          transition: border-color 0.15s;
        }
        .devhub-idea-card:hover {
          border-color: var(--accent, #3b82f6);
        }
        .devhub-idea-card svg {
          color: var(--accent, #3b82f6);
          margin-bottom: 8px;
        }
        .devhub-idea-card h5 {
          margin: 0 0 6px;
          font-size: 0.88rem;
          font-weight: 600;
          color: var(--text-primary, #e4e4e7);
        }
        .devhub-idea-card p {
          margin: 0;
          font-size: 0.82rem;
          color: var(--text-muted, #a1a1aa);
          line-height: 1.5;
        }

        /* Tips list */
        .devhub-tips-list {
          list-style: none;
          padding: 0;
        }
        .devhub-tips-list li {
          padding: 10px 14px;
          border-left: 3px solid var(--accent, #3b82f6);
          margin-bottom: 10px;
          background: var(--bg-tertiary, #0f0f12);
          border-radius: 0 8px 8px 0;
        }

        /* Footer */
        .devhub-footer {
          text-align: center;
          margin-top: 32px;
          padding-top: 20px;
          border-top: 1px solid var(--border, #27272a);
          color: var(--text-muted, #71717a);
          font-size: 0.82rem;
        }
      `}</style>
    </div>
  );
}
