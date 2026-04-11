# Einstein

**Your Personal Semantic Engine** — turns scattered thoughts, notes, emails, and messages into an intelligent, searchable knowledge graph with predictive insights.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/react-18-61DAFB?logo=react&logoColor=white)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/fastapi-0.104+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/postgresql-13+-4169E1?logo=postgresql&logoColor=white)](https://postgresql.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## What It Does

Einstein captures context from every tool you use — email, Slack, GitHub, Jira, Zoom, meetings, notes — and weaves it into a single knowledge graph. It surfaces what matters: who's going dormant, what's overdue, which relationships need attention, and what's likely to happen next.

---

## Features

### Brain & Knowledge Graph
- **Semantic Knowledge Graph** — entities, relationships, and topics extracted automatically from your notes and events
- **Interactive Graph View** — explore connections between people, projects, and ideas visually
- **Smart Search** — natural language queries across your entire knowledge base
- **Ask AI (RAG)** — conversational Q&A grounded in your own data

### Context Capture
- **Vault Notes** — Markdown-first note-taking with folders, frontmatter, outgoing links, and version history
- **Meeting Briefings** — auto-generated prep packs before calls
- **Action Items** — extracted from notes and tracked across projects
- **Decisions Log** — record reasoning, alternatives, and revisit dates
- **Calendar Events** — linked to notes and people

### People & Relationships
- **People Profiles** — auto-built dossiers from every interaction
- **Dormancy Detection** — flags relationships going cold before they break
- **Freshness Scoring** — quantifies how active each connection is
- **Interaction Timeline** — full history per person

### Projects
- **Project Tracking** — status, deadlines, linked notes, associated people
- **Activity Monitoring** — dormancy alerts for stale projects
- **Cross-linking** — notes, actions, and events connected to projects automatically

### Insights & Predictions
- **Activity Heatmap** — 60-day activity patterns across all sources
- **Trend Detection** — increasing, decreasing, or stable activity analysis
- **Forecasting** — time-series predictions using statistical models (Holt-Winters) with optional deep learning backends
- **Dormancy Risk** — predictive alerts for people and projects at risk of going inactive
- **Forecast Accuracy** — retrospective MAPE, MAE, and coverage tracking

### Integrations
- **Gmail** — auto-capture emails
- **Outlook** — Microsoft email sync
- **Slack** — channel messages
- **GitHub** — PRs, issues, reviews
- **Jira** — issue tracking
- **Zoom** — meeting transcripts
- **Linear** — project tracking
- **Telegram** — bot messages & channels
- **Google Calendar** — event sync (via Gmail)
- **OAuth2 Flows** — connect with one click, credentials stored securely
- **Webhook Ingestion** — real-time event capture

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     React Frontend (Vite)                     │
│  BrainHome · Graph · Files · People · Projects · Insights    │
│  Meetings · Actions · Ask AI · Integrations · Calendar       │
└──────────────────────┬───────────────────────────────────────┘
                       │ REST API
┌──────────────────────▼───────────────────────────────────────┐
│                    FastAPI Backend                            │
│  15 route modules · Auth middleware · Error handlers         │
├──────────────────────────────────────────────────────────────┤
│  Domain          │  Application       │  Infrastructure      │
│  · Entities      │  · Use Cases       │  · PostgreSQL        │
│  · Repositories  │  · Orchestration   │  · Pinecone (vector) │
│  · Services      │  · Validation      │  · Redis + ARQ       │
│                  │                    │  · 9 Connectors      │
│                  │                    │  · Forecasting       │
└──────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React 18, TypeScript, Vite, Tauri (desktop), Lucide icons |
| **Backend** | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy (async) |
| **Database** | PostgreSQL 13+ with asyncpg |
| **Vector Search** | Pinecone, OpenAI embeddings |
| **AI / LLM** | OpenAI GPT, LiteLLM |
| **Background Jobs** | ARQ + Redis (cron workers, sync tasks) |
| **Auth** | JWT (python-jose), bcrypt |
| **Deployment** | Vercel (serverless), Docker |

---

## Getting Started

Einstein supports two modes: **Local** (everything on your machine) and **Cloud** (managed services). The in-app **Getting Started** wizard walks you through either path with live status checks.

### Quick Start: Local (free, private, offline)

```bash
# 1. Clone & install
git clone https://github.com/Phani3108/Einstein.git
cd Einstein
pip install -e '.[local]'

# 2. Install Ollama (local AI) — https://ollama.com
ollama pull llama3.2
ollama pull nomic-embed-text

# 3. Configure
cat > .env << 'EOF'
DATABASE_URL=sqlite+aiosqlite:///einstein.db
LLM_MODEL=ollama/llama3.2
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
EOF

# 4. Start
uvicorn src.api.app:app --reload --port 8000

# 5. Frontend (new terminal)
cd app && npm install && npm run dev
```

Open [http://localhost:5173](http://localhost:5173) — click **Getting Started** in the sidebar.

### Quick Start: Cloud

```bash
# 1. Clone & install
git clone https://github.com/Phani3108/Einstein.git
cd Einstein
pip install -e .
cd app && npm install && cd ..

# 2. Configure
cp .env.example .env
# Edit .env with your credentials:
#   DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
#   OPENAI_API_KEY=sk-...
#   LLM_MODEL=gpt-4

# 3. Initialize & run
python scripts/init_db.py
uvicorn src.api.app:app --reload
cd app && npm run dev
```

### Prerequisites

| Mode | Requirements |
|------|-------------|
| **Local** | Python 3.11+, Node.js 18+, [Ollama](https://ollama.com) |
| **Cloud** | Python 3.11+, Node.js 18+, PostgreSQL, OpenAI API key |

### Seed Sample Data (optional)

```bash
curl -X POST http://localhost:8000/api/v1/dev/seed
```

---

## Project Structure

```
Einstein/
├── app/                    # React frontend (Vite + TypeScript)
│   └── src/
│       ├── components/     # 40+ UI components
│       ├── lib/            # API client, state management
│       └── App.tsx         # Root with onboarding flow
├── src/                    # Python backend
│   ├── api/                # FastAPI routes (15 modules)
│   ├── application/        # Use cases & orchestration
│   ├── domain/             # Entities, enums, interfaces
│   └── infrastructure/     # DB, connectors, prediction, tasks
├── scripts/                # DB init, seeding, utilities
├── migrations/             # Alembic database migrations
├── tests/                  # Test suite
├── browser-extension/      # Chrome extension (capture)
├── mobile/                 # Mobile app scaffold
└── einstein-cli/           # CLI tool
```

---

## API Endpoints

| Group | Prefix | Purpose |
|-------|--------|---------|
| Vault | `/api/v1/vault` | Notes, decisions, config, files |
| Thoughts | `/api/v1/thoughts` | Thought capture & retrieval |
| Search | `/api/v1/search` | Semantic + hybrid search |
| Context | `/api/v1/context` | Events, people, projects |
| Insights | `/api/v1/insights` | Briefings, activity, dormancy |
| Actions | `/api/v1/actions` | Action items CRUD |
| Integrations | `/api/v1/integrations` | OAuth connect, sync, webhooks |
| Predictions | `/api/v1/predictions` | Forecasts, accuracy, status |
| Intelligence | `/api/v1/intelligence` | AI analysis & suggestions |
| AI Tools | `/api/v1/ai` | Ask AI (RAG), summarization |
| Timeline | `/api/v1/timeline` | Chronological event view |
| Reflection | `/api/v1/reflection` | Weekly digests, patterns |
| Distillation | `/api/v1/distillation` | Note condensation |
| Admin | `/api/v1/admin` | User management, health |
| Dev | `/api/v1/dev` | Seed data (dev only) |

Interactive docs available at `/api/v1/docs` when the server is running.

---

## Mock Data

The seed script creates a realistic, interconnected dataset for a startup founder building "Nexus":

- **7 people** — co-founder, designer, engineer, investor, advisor, customer, freelancer
- **4 projects** — MVP, fundraising, marketing, enterprise pilot
- **15 vault notes** — meetings, journals, specs, brainstorms, decisions
- **10 action items** — varied priorities, statuses, and deadlines
- **6 calendar events** — upcoming meetings and reminders
- **30 context events** — emails, Slack, GitHub, calendar across 60 days
- **16 semantic entities** — people, orgs, topics, technologies
- **11 entity relationships** — builds, works_at, advocates, implements
- **4 decisions** — with reasoning and alternatives
- **4 commitments** — tracked promises to people

All data is idempotent and can be re-run safely.

---

## Deployment

### Vercel

The project deploys as a monorepo on Vercel:

- **Frontend** — built with `npm run build` from `app/`, served as static files
- **Backend** — Python serverless function via `api/index.py`
- **Config** — see `vercel.json` for routing rules

### Environment Variables (Vercel)

Set `DATABASE_URL`, `OPENAI_API_KEY`, `PINECONE_API_KEY`, and `JWT_SECRET` in the Vercel dashboard.

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Follow conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`
4. Push and open a pull request

---

## License

MIT — see [LICENSE](LICENSE) for details.
