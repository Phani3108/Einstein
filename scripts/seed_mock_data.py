"""Seed mock data for Einstein development.

Creates a rich, interconnected dataset for a startup founder building "Nexus" -
a collaboration platform. All data is idempotent via ON CONFLICT DO NOTHING.
"""
import asyncio
import json
import os
import ssl
import sys
import uuid
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()

# ---------------------------------------------------------------------------
# Deterministic UUIDs
# ---------------------------------------------------------------------------
NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

USER_ID = uuid.UUID("60bd95e0-1d86-49a0-99c4-1b72773ba450")

PEOPLE_IDS = {
    "sarah": uuid.uuid5(NS, "person-sarah-chen"),
    "marcus": uuid.uuid5(NS, "person-marcus-rivera"),
    "priya": uuid.uuid5(NS, "person-priya-patel"),
    "david": uuid.uuid5(NS, "person-david-kim"),
    "emma": uuid.uuid5(NS, "person-emma-thompson"),
    "james": uuid.uuid5(NS, "person-james-liu"),
    "anika": uuid.uuid5(NS, "person-anika-sharma"),
}

PROJECT_IDS = {
    "nexus_mvp": uuid.uuid5(NS, "project-nexus-mvp"),
    "seed_fundraising": uuid.uuid5(NS, "project-seed-fundraising"),
    "marketing_launch": uuid.uuid5(NS, "project-marketing-launch"),
    "enterprise_pilot": uuid.uuid5(NS, "project-enterprise-pilot"),
}

NOTE_IDS = {
    "team-standup-apr-7": uuid.uuid5(NS, "note-team-standup-apr-7"),
    "investor-call-david": uuid.uuid5(NS, "note-investor-call-david"),
    "design-review-q2": uuid.uuid5(NS, "note-design-review-q2"),
    "nexus-mvp-spec": uuid.uuid5(NS, "note-nexus-mvp-spec"),
    "fundraising-tracker": uuid.uuid5(NS, "note-fundraising-tracker"),
    "marketing-plan": uuid.uuid5(NS, "note-marketing-plan"),
    "enterprise-pilot-notes": uuid.uuid5(NS, "note-enterprise-pilot-notes"),
    "daily-apr-7": uuid.uuid5(NS, "note-daily-apr-7"),
    "daily-apr-6": uuid.uuid5(NS, "note-daily-apr-6"),
    "weekly-reflection-w14": uuid.uuid5(NS, "note-weekly-reflection-w14"),
    "payment-provider": uuid.uuid5(NS, "note-payment-provider"),
    "target-market": uuid.uuid5(NS, "note-target-market"),
    "feature-prioritization": uuid.uuid5(NS, "note-feature-prioritization"),
    "brand-identity": uuid.uuid5(NS, "note-brand-identity"),
    "competitor-analysis": uuid.uuid5(NS, "note-competitor-analysis"),
}

ACTION_IDS = [uuid.uuid5(NS, f"action-{i}") for i in range(10)]
CALENDAR_IDS = [uuid.uuid5(NS, f"calendar-{i}") for i in range(6)]
DECISION_IDS = [uuid.uuid5(NS, f"decision-{i}") for i in range(4)]
CONTEXT_EVENT_IDS = [uuid.uuid5(NS, f"context-event-{i}") for i in range(30)]
THOUGHT_IDS = [uuid.uuid5(NS, f"thought-{i}") for i in range(6)]
SEMANTIC_IDS = [uuid.uuid5(NS, f"semantic-{i}") for i in range(16)]
RELATIONSHIP_IDS = [uuid.uuid5(NS, f"entity-rel-{i}") for i in range(11)]
NOTE_ASSOC_IDS = [uuid.uuid5(NS, f"note-assoc-{i}") for i in range(16)]
COMMITMENT_IDS = [uuid.uuid5(NS, f"commitment-{i}") for i in range(4)]
CONNECTION_IDS = [uuid.uuid5(NS, f"connection-{i}") for i in range(6)]

NOW = datetime.utcnow()


def ts(delta_days: float = 0, delta_hours: float = 0) -> str:
    """ISO timestamp relative to now."""
    dt = NOW + timedelta(days=delta_days, hours=delta_hours)
    return dt.isoformat()


def date_str(delta_days: int = 0) -> str:
    """Date string YYYY-MM-DD relative to now."""
    return (NOW + timedelta(days=delta_days)).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# INSERT helpers
# ---------------------------------------------------------------------------

async def insert_user(conn):
    print("  Inserting user...")
    await conn.execute(text("""
        INSERT INTO users (id, email, hashed_password, is_active, is_admin, created_at, updated_at)
        VALUES (:id, :email, :hashed_password, :is_active, :is_admin, :created_at, :updated_at)
        ON CONFLICT DO NOTHING
    """), {
        "id": str(USER_ID),
        "email": "founder@nexus.io",
        "hashed_password": "$2b$12$LJ3m4ks9Yz0Qx5Xz5Xz5XuAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        "is_active": True,
        "is_admin": True,
        "created_at": ts(-90),
        "updated_at": ts(),
    })


async def insert_people(conn):
    print("  Inserting people...")
    people = [
        {
            "id": str(PEOPLE_IDS["sarah"]),
            "user_id": str(USER_ID),
            "name": "Sarah Chen",
            "aliases": ["Sarah", "SC"],
            "phone": "+1-415-555-0101",
            "email": "sarah@nexus.io",
            "role": "Co-founder/CTO",
            "organization": "Nexus",
            "last_seen": ts(-2),
            "interaction_count": 47,
            "notes": "Co-founder and technical lead. Expert in distributed systems. Met at Stanford CS program.",
            "freshness_score": 0.92,
            "last_activity_at": ts(-2),
            "dormancy_days": 2,
            "created_at": ts(-90),
        },
        {
            "id": str(PEOPLE_IDS["marcus"]),
            "user_id": str(USER_ID),
            "name": "Marcus Rivera",
            "aliases": ["Marcus", "MR"],
            "phone": "+1-415-555-0102",
            "email": "marcus@nexus.io",
            "role": "Lead Designer",
            "organization": "Nexus",
            "last_seen": ts(-5),
            "interaction_count": 28,
            "notes": "Lead designer with background in enterprise UX. Previously at Figma. Strong visual design and interaction patterns.",
            "freshness_score": 0.75,
            "last_activity_at": ts(-5),
            "dormancy_days": 5,
            "created_at": ts(-75),
        },
        {
            "id": str(PEOPLE_IDS["priya"]),
            "user_id": str(USER_ID),
            "name": "Priya Patel",
            "aliases": ["Priya", "PP"],
            "phone": "+1-415-555-0103",
            "email": "priya@nexus.io",
            "role": "Backend Engineer",
            "organization": "Nexus",
            "last_seen": ts(-1),
            "interaction_count": 52,
            "notes": "Backend engineer, strong in Python and Go. Handles auth, API design, and infrastructure. Very reliable.",
            "freshness_score": 0.95,
            "last_activity_at": ts(-1),
            "dormancy_days": 1,
            "created_at": ts(-60),
        },
        {
            "id": str(PEOPLE_IDS["david"]),
            "user_id": str(USER_ID),
            "name": "David Kim",
            "aliases": ["David", "DK"],
            "phone": "+1-650-555-0201",
            "email": "david@kv-capital.com",
            "role": "Investor",
            "organization": "KV Capital",
            "last_seen": ts(-12),
            "interaction_count": 8,
            "notes": "Managing partner at KV Capital. Focused on developer tools and B2B SaaS. Warm intro from Mike at a]16z.",
            "freshness_score": 0.35,
            "last_activity_at": ts(-12),
            "dormancy_days": 12,
            "created_at": ts(-45),
        },
        {
            "id": str(PEOPLE_IDS["emma"]),
            "user_id": str(USER_ID),
            "name": "Emma Thompson",
            "aliases": ["Emma", "ET"],
            "phone": "+1-415-555-0301",
            "email": "emma@growthlab.co",
            "role": "Marketing Advisor",
            "organization": "GrowthLab",
            "last_seen": ts(-8),
            "interaction_count": 15,
            "notes": "Marketing advisor, previously VP Marketing at Notion. Expert in PLG and developer marketing.",
            "freshness_score": 0.55,
            "last_activity_at": ts(-8),
            "dormancy_days": 8,
            "created_at": ts(-40),
        },
        {
            "id": str(PEOPLE_IDS["james"]),
            "user_id": str(USER_ID),
            "name": "James Liu",
            "aliases": ["James", "JL"],
            "phone": "+1-212-555-0401",
            "email": "james@acmecorp.com",
            "role": "Customer (Enterprise)",
            "organization": "Acme Corp",
            "last_seen": ts(-15),
            "interaction_count": 6,
            "notes": "VP Engineering at Acme Corp. Interested in Nexus for their 200-person eng team. Enterprise pilot contact.",
            "freshness_score": 0.25,
            "last_activity_at": ts(-15),
            "dormancy_days": 15,
            "created_at": ts(-30),
        },
        {
            "id": str(PEOPLE_IDS["anika"]),
            "user_id": str(USER_ID),
            "name": "Anika Sharma",
            "aliases": ["Anika", "AS"],
            "phone": "+1-415-555-0501",
            "email": "anika@freelance.dev",
            "role": "Content Writer",
            "organization": "Freelance",
            "last_seen": ts(-18),
            "interaction_count": 4,
            "notes": "Freelance content writer specializing in developer tools. Writing blog posts and landing page copy for launch.",
            "freshness_score": 0.15,
            "last_activity_at": ts(-18),
            "dormancy_days": 18,
            "created_at": ts(-25),
        },
    ]
    for p in people:
        await conn.execute(text("""
            INSERT INTO people (id, user_id, name, aliases, phone, email, role, organization,
                                last_seen, interaction_count, notes, freshness_score,
                                last_activity_at, dormancy_days, created_at)
            VALUES (:id, :user_id, :name, :aliases, :phone, :email, :role, :organization,
                    :last_seen, :interaction_count, :notes, :freshness_score,
                    :last_activity_at, :dormancy_days, :created_at)
            ON CONFLICT DO NOTHING
        """), p)


async def insert_projects(conn):
    print("  Inserting projects...")
    projects = [
        {
            "id": str(PROJECT_IDS["nexus_mvp"]),
            "user_id": str(USER_ID),
            "title": "Nexus MVP",
            "description": "Build the core product: auth, dashboard, API, real-time collaboration",
            "status": "active",
            "deadline": ts(30),
            "last_activity_at": ts(-1),
            "dormancy_days": 1,
            "created_at": ts(-60),
            "updated_at": ts(-1),
        },
        {
            "id": str(PROJECT_IDS["seed_fundraising"]),
            "user_id": str(USER_ID),
            "title": "Seed Fundraising",
            "description": "Close $1.5M seed round. Target: 3 term sheets by end of month",
            "status": "active",
            "deadline": ts(21),
            "last_activity_at": ts(-5),
            "dormancy_days": 5,
            "created_at": ts(-45),
            "updated_at": ts(-5),
        },
        {
            "id": str(PROJECT_IDS["marketing_launch"]),
            "user_id": str(USER_ID),
            "title": "Marketing Launch",
            "description": "Pre-launch marketing: landing page, blog content, social media, launch event",
            "status": "active",
            "deadline": ts(45),
            "last_activity_at": ts(-3),
            "dormancy_days": 3,
            "created_at": ts(-30),
            "updated_at": ts(-3),
        },
        {
            "id": str(PROJECT_IDS["enterprise_pilot"]),
            "user_id": str(USER_ID),
            "title": "Enterprise Pilot",
            "description": "Acme Corp pilot deployment. 50-user trial with dedicated support",
            "status": "active",
            "deadline": ts(60),
            "last_activity_at": ts(-8),
            "dormancy_days": 8,
            "created_at": ts(-20),
            "updated_at": ts(-8),
        },
    ]
    for p in projects:
        await conn.execute(text("""
            INSERT INTO projects (id, user_id, title, description, status, deadline,
                                  last_activity_at, dormancy_days, created_at, updated_at)
            VALUES (:id, :user_id, :title, :description, :status, :deadline,
                    :last_activity_at, :dormancy_days, :created_at, :updated_at)
            ON CONFLICT DO NOTHING
        """), p)


async def insert_notes(conn):
    print("  Inserting vault notes...")
    notes = [
        {
            "id": str(NOTE_IDS["team-standup-apr-7"]),
            "user_id": str(USER_ID),
            "file_path": "meetings/team-standup-apr-7.md",
            "title": "Team Standup - April 7",
            "content": """# Team Standup - April 7

## Attendees
Sarah Chen, Priya Patel, Marcus Rivera

## Updates

### Sarah Chen
Sarah gave an update on the infrastructure side. She's been working on the Kubernetes cluster configuration for the Nexus MVP deployment. The auto-scaling policies are now in place, and she ran stress tests over the weekend that showed we can handle up to 10k concurrent WebSocket connections. She flagged that we need to decide on the message queue — she's leaning toward NATS over RabbitMQ for the real-time collaboration features.

Sarah also mentioned she had a brief email exchange with David Kim from KV Capital about our technical architecture. David was impressed by our approach to event sourcing and wants to discuss it more during the next investor call. She'll prepare a one-page technical architecture overview for David before the call.

### Priya Patel
Priya shipped the authentication module yesterday. OAuth2 with Google and GitHub is working, and she's now adding magic link support. The PR is up for review — she mentioned she'd appreciate eyes on the token rotation logic specifically. She estimates the full auth flow including email verification will be done by end of week.

Priya also brought up the API rate limiting strategy. She's proposing a tiered approach: free tier at 100 req/min, pro at 1000, enterprise at 10k. This ties into the pricing discussions we've been having with Emma Thompson for the Marketing Launch.

### Marcus Rivera
Marcus presented the updated dashboard wireframes. He incorporated feedback from last week's design review with Sarah. The key changes include a collapsible sidebar, keyboard shortcuts for power users, and a new activity feed component. He's planning to run user testing with 5 potential beta users next week.

Marcus also shared the new icon set he designed — clean, minimal, consistent with our brand direction. Anika Sharma will need these for the blog post she's writing about our design philosophy.

## Action Items
- Review Priya's auth PR (priority: today)
- Sarah to prepare tech architecture doc for David Kim
- Marcus to schedule user testing sessions
- Discuss API rate limiting tiers at next standup""",
            "frontmatter": json.dumps({"type": "meeting", "attendees": ["Sarah Chen", "Priya Patel", "Marcus Rivera"]}),
            "outgoing_links": json.dumps(["projects/nexus-mvp-spec.md", "decisions/payment-provider.md"]),
            "is_bookmarked": True,
            "created_at": ts(-1),
            "updated_at": ts(-1),
        },
        {
            "id": str(NOTE_IDS["investor-call-david"]),
            "user_id": str(USER_ID),
            "file_path": "meetings/investor-call-david.md",
            "title": "Investor Call - David Kim",
            "content": """# Investor Call - David Kim (KV Capital)

## Meeting Context
Call with David Kim, Managing Partner at KV Capital. This is our third conversation. David was introduced through a warm connection and has expressed strong interest in our seed round.

## Discussion Points

### Product Vision
I walked David through the full Nexus vision — how we're building the collaboration layer that sits between existing tools rather than replacing them. David was particularly interested in our event-driven architecture and how it enables real-time sync across different data sources. He compared it to what Zapier did for automation but for real-time collaboration context.

David asked pointed questions about our technical moat. I explained our approach to conflict-free replicated data types (CRDTs) for real-time editing, and how Sarah Chen has designed the system to handle offline-first scenarios gracefully. He seemed impressed by the depth of our technical approach.

### Market Opportunity
We discussed the $47B collaboration tools market. David's thesis aligns well with ours — he believes the market is fragmented and there's room for a platform play. He mentioned that two of his portfolio companies (both Series B) are struggling with exactly the problem Nexus solves.

I shared our early traction numbers: 200+ waitlist signups in 2 weeks from a single HN post, and the Acme Corp enterprise pilot with James Liu. David was encouraged by the enterprise interest this early.

### Fundraising Details
David confirmed KV Capital is interested in leading or co-leading our $1.5M seed round. He wants to see:
1. A working demo (target: 2 weeks)
2. At least one paying pilot customer (Acme Corp timeline)
3. Updated financial projections

He mentioned typical check size for KV Capital at seed is $500K-$750K. He's comfortable with a $8-10M post-money valuation given our team and early traction.

### Follow-up Items
- Send David the updated pitch deck with revised TAM analysis
- Schedule a demo session once the MVP core features are ready
- Connect David with James Liu from Acme Corp for a reference call
- Share Sarah's technical architecture document

## My Assessment
David is a strong potential lead investor. His portfolio companies would be great design partners. Need to maintain momentum — the 2-week demo timeline is aggressive but achievable if Priya and Sarah stay focused on the Nexus MVP.""",
            "frontmatter": json.dumps({"type": "meeting", "attendees": ["David Kim"]}),
            "outgoing_links": json.dumps(["projects/fundraising-tracker.md", "projects/nexus-mvp-spec.md"]),
            "is_bookmarked": True,
            "created_at": ts(-12),
            "updated_at": ts(-10),
        },
        {
            "id": str(NOTE_IDS["design-review-q2"]),
            "user_id": str(USER_ID),
            "file_path": "meetings/design-review-q2.md",
            "title": "Design Review Q2",
            "content": """# Design Review Q2

## Attendees
Marcus Rivera, Sarah Chen

## Overview
Quarterly design review to align on the visual direction and UX patterns for Q2. Marcus presented the design system updates and Sarah provided technical feasibility feedback.

## Design System Updates

### Component Library
Marcus has been refactoring the component library to use a token-based design system. All colors, spacing, and typography are now defined as tokens, making theme switching (including dark mode) much simpler. He showed a prototype of the dark mode toggle — it's smooth and preserves user preference across sessions.

The button component set has been expanded to include ghost, outline, and gradient variants. Sarah confirmed these are straightforward to implement with our current Tailwind setup. Marcus flagged that the gradient buttons might need a fallback for older browsers, but Sarah said our target browser support (last 2 versions of Chrome, Firefox, Safari, Edge) handles them fine.

### Dashboard Redesign
The main dashboard is being redesigned around a "workspace" metaphor. Instead of a static grid, users will have customizable panels that can be rearranged, resized, and configured. Marcus showed three layout presets: Focus (single panel), Split (two panel), and Command Center (multi-panel with sidebar).

Sarah raised a concern about the real-time collaboration overlay — when multiple users are viewing the same workspace, we need to show presence indicators without cluttering the UI. Marcus proposed small avatar badges in the corner of each panel, with a full collaboration sidebar that can be toggled. This felt like the right balance.

### Mobile Responsive Strategy
We agreed to take a progressive approach to mobile. The initial launch will be web-first with responsive layouts for tablet. True mobile optimization will come in Q3 after we validate the core experience on desktop. This aligns with our decision to delay the mobile app.

Marcus is designing adaptive layouts that work well from 768px up. Below that, we'll show a simplified read-only view with a prompt to use the desktop version for full functionality.

## Brand Consistency
Marcus and I discussed the brand direction with reference to the work Anika Sharma is doing on content. We need to ensure the visual language in the app matches what we're putting out in marketing materials. Marcus will share the updated brand guidelines with Anika and Emma Thompson so everyone is aligned.

## Next Steps
- Marcus to finalize the dashboard component specs by end of week
- Sarah to prototype the workspace panel drag-and-drop system
- Schedule user testing for the new dashboard with 5 beta candidates
- Review brand guidelines with Anika and Emma before the Marketing Launch push""",
            "frontmatter": json.dumps({"type": "meeting", "attendees": ["Marcus Rivera", "Sarah Chen"]}),
            "outgoing_links": json.dumps(["brainstorms/brand-identity.md", "projects/nexus-mvp-spec.md"]),
            "is_bookmarked": False,
            "created_at": ts(-5),
            "updated_at": ts(-5),
        },
        {
            "id": str(NOTE_IDS["nexus-mvp-spec"]),
            "user_id": str(USER_ID),
            "file_path": "projects/nexus-mvp-spec.md",
            "title": "Nexus MVP Specification",
            "content": """# Nexus MVP Specification

## Vision
Nexus is a real-time collaboration platform that unifies team communication, document editing, and project management into a single coherent workspace. Unlike tools that try to replace existing workflows, Nexus integrates with what teams already use and adds a real-time collaboration layer on top.

## Core Features (MVP Scope)

### 1. Authentication & User Management
Owner: Priya Patel
Status: In Progress (80% complete)

The auth system supports multiple providers:
- OAuth2 (Google, GitHub) — DONE
- Magic link email auth — IN PROGRESS
- SSO/SAML for enterprise — PLANNED for Enterprise Pilot

Priya has implemented JWT-based session management with automatic token rotation. The refresh token flow uses secure HTTP-only cookies. Rate limiting is in place for auth endpoints (10 attempts per minute per IP).

Key technical decisions:
- Using Argon2id for password hashing (over bcrypt) for better resistance to GPU attacks
- Session tokens expire after 24 hours, refresh tokens after 30 days
- Implementing device fingerprinting for suspicious login detection

### 2. Dashboard & Workspace
Owner: Marcus Rivera (design) + Sarah Chen (implementation)
Status: Design Complete, Implementation 40%

The dashboard follows a workspace paradigm with three layout presets (Focus, Split, Command Center). Key components:
- Activity feed with real-time updates via WebSocket
- Quick action bar with keyboard shortcuts (Cmd+K)
- Customizable widget panels (calendar, tasks, team activity)
- Presence indicators showing active team members

### 3. Real-time Collaboration Engine
Owner: Sarah Chen
Status: Architecture Complete, Implementation 30%

Built on CRDTs (Conflict-free Replicated Data Types) using Yjs library. The system supports:
- Concurrent document editing with automatic conflict resolution
- Cursor presence and selection highlighting
- Change awareness (what changed while you were away)
- Offline support with automatic sync on reconnection

Infrastructure: WebSocket connections managed through a NATS-based message broker. Sarah's stress tests show the system handles 10k concurrent connections with <50ms latency for change propagation.

### 4. API Layer
Owner: Priya Patel
Status: 60% complete

RESTful API with OpenAPI documentation. Key endpoints:
- `/api/v1/workspaces` — CRUD for workspaces
- `/api/v1/documents` — Document management with versioning
- `/api/v1/collaborators` — Team management
- `/api/v1/activity` — Activity feed with pagination

Rate limiting tiers:
- Free: 100 requests/minute
- Pro: 1,000 requests/minute
- Enterprise: 10,000 requests/minute (aligned with Acme Corp pilot needs)

## Technical Stack
- Frontend: React 18, TypeScript, Tailwind CSS, Zustand
- Backend: Python (FastAPI), PostgreSQL, Redis
- Real-time: WebSocket, NATS, Yjs (CRDTs)
- Infrastructure: Kubernetes (EKS), Terraform, GitHub Actions

## Timeline
- Week 1-2: Complete auth + basic dashboard
- Week 3: Real-time collaboration beta
- Week 4: API polish + documentation
- Week 5: Internal testing + bug fixes
- Week 6: Beta launch to waitlist (200+ signups)

## Dependencies
- Stripe integration for billing (see payment provider decision)
- Brand assets from Marcus and Anika for the onboarding flow
- Enterprise SSO requires coordination with James Liu at Acme Corp""",
            "frontmatter": json.dumps({"type": "project", "status": "active", "project": "Nexus MVP"}),
            "outgoing_links": json.dumps(["decisions/payment-provider.md", "meetings/team-standup-apr-7.md"]),
            "is_bookmarked": True,
            "created_at": ts(-45),
            "updated_at": ts(-2),
        },
        {
            "id": str(NOTE_IDS["fundraising-tracker"]),
            "user_id": str(USER_ID),
            "file_path": "projects/fundraising-tracker.md",
            "title": "Fundraising Tracker",
            "content": """# Seed Fundraising Tracker

## Round Parameters
- Target: $1.5M seed round
- Valuation target: $8-10M post-money
- Timeline: Close within 3 weeks
- Use of funds: 18 months runway (team of 6-8)

## Investor Pipeline

### Tier 1 — Active Conversations
| Investor | Fund | Check Size | Status | Next Step |
|----------|------|-----------|--------|-----------|
| David Kim | KV Capital | $500-750K | Very Interested | Demo in 2 weeks |
| Lisa Park | Gradient Ventures | $300K | Interested | Pitch scheduled |
| Raj Mehta | TechStars Alumni Fund | $200K | Warm intro made | Follow up |

### Tier 2 — Early Outreach
| Investor | Fund | Status |
|----------|------|--------|
| Amy Foster | Sequoia Scout | Email sent |
| Tom Bradley | YC Alumni Fund | Intro requested |
| Nina Patel | Heavybit | Researching |

## Key Milestones for Close
1. Working demo (target: 2 weeks) — David Kim needs this
2. At least one signed pilot (Acme Corp with James Liu)
3. Updated financials with 18-month projections
4. Term sheet from KV Capital (would trigger FOMO from others)

## Financial Projections Summary
- Burn rate: ~$80K/month (current team of 4)
- Post-raise team: 6-8 people (2 engineers, 1 designer, 1 marketing)
- Revenue projection: $0 → $50K ARR in first 6 months (enterprise pilots)
- Target: $500K ARR by month 18

## Pitch Deck Status
The current deck is v3. Emma Thompson reviewed it and suggested:
- Lead with the problem story, not the solution
- Add a competitive landscape slide with clear differentiation
- Include the Acme Corp pilot as social proof
- Reduce technical slides (save for appendix)

I need to incorporate Emma's feedback and send the updated version to David Kim before our next call. Also need to prepare detailed financial model in a separate appendix — David specifically asked for unit economics assumptions.

## Notes from Previous Conversations
David Kim was most excited about:
- Our CRDT-based real-time engine (technical differentiation)
- Enterprise interest this early (Acme Corp pilot)
- Team background (Sarah's distributed systems experience, Marcus's Figma tenure)

He was concerned about:
- Go-to-market strategy (addressed by Emma's involvement)
- Competition from established players (Notion, Coda)
- Burn rate assumptions (need to tighten projections)""",
            "frontmatter": json.dumps({"type": "project", "status": "active", "project": "Seed Fundraising"}),
            "outgoing_links": json.dumps(["meetings/investor-call-david.md", "projects/enterprise-pilot-notes.md"]),
            "is_bookmarked": True,
            "created_at": ts(-30),
            "updated_at": ts(-3),
        },
        {
            "id": str(NOTE_IDS["marketing-plan"]),
            "user_id": str(USER_ID),
            "file_path": "projects/marketing-plan.md",
            "title": "Marketing Launch Plan",
            "content": """# Marketing Launch Plan

## Overview
Pre-launch marketing campaign for Nexus. Goal: build awareness, grow waitlist to 1000+, and establish thought leadership in the collaboration tools space before official launch.

## Team
- Emma Thompson (Marketing Advisor) — strategy, PLG playbook, channel optimization
- Anika Sharma (Content Writer) — blog posts, landing page copy, social content
- Marcus Rivera (Design) — visual assets, brand consistency

## Channel Strategy

### 1. Content Marketing (Primary)
Blog posts targeting developer and team-lead audiences:

**Planned Posts:**
1. "Why Your Team's Tools Don't Talk to Each Other" — Problem awareness piece (Anika drafting)
2. "The Case for Real-Time Collaboration Beyond Docs" — Thought leadership
3. "How We Built Our CRDT Engine" — Technical deep-dive by Sarah Chen
4. "From Side Project to Seed Round: Our Journey" — Founder story

Emma reviewed the content calendar and suggested we front-load the problem-awareness content before revealing the product. She calls it the "pull strategy" — create demand before supply.

Anika Sharma is writing the first two posts. She needs the pricing page copy finalized ASAP so we can align messaging across all content. I've asked her to have drafts ready for review by next week.

### 2. Social Media
- Twitter/X: Daily insights about collaboration, remote work, and tool fatigue
- LinkedIn: Weekly long-form posts, cross-post blog content
- HN/Reddit: Strategic posts in relevant communities (already got 200 signups from one HN post)

### 3. Landing Page
Current landing page converts at 4.2%. Emma thinks we can get to 8%+ with:
- Stronger hero section (show, don't tell)
- Social proof (waitlist count, Acme Corp logo with permission from James Liu)
- Interactive demo embed (needs Marcus to design, Priya to build)

### 4. Launch Event
Planning a virtual launch event — "The Future of Team Collaboration"
- Date: ~6 weeks out
- Format: 30-min product demo + 15-min Q&A
- Speakers: me + Sarah Chen
- Pre-registration as waitlist growth mechanism

## Budget
- Content: $3K (Anika's freelance rate for 4 posts + landing page copy)
- Design: In-house (Marcus)
- Paid acquisition: $2K experiment budget (after organic baseline established)
- Event platform: $500

## Metrics & Goals
- Waitlist: 200 → 1000+ by launch
- Landing page conversion: 4.2% → 8%+
- Blog traffic: 500 unique visitors/month
- Social following: 500+ combined

## Timeline
- Week 1-2: Content production + landing page redesign
- Week 3: Social media campaign launch
- Week 4: First blog post published
- Week 5-6: Ramp up + launch event prep""",
            "frontmatter": json.dumps({"type": "project", "status": "active", "project": "Marketing Launch"}),
            "outgoing_links": json.dumps(["brainstorms/brand-identity.md", "reference/competitor-analysis.md"]),
            "is_bookmarked": False,
            "created_at": ts(-20),
            "updated_at": ts(-2),
        },
        {
            "id": str(NOTE_IDS["enterprise-pilot-notes"]),
            "user_id": str(USER_ID),
            "file_path": "projects/enterprise-pilot-notes.md",
            "title": "Enterprise Pilot - Acme Corp",
            "content": """# Enterprise Pilot — Acme Corp

## Overview
Acme Corp has agreed to a 50-user pilot of Nexus within their engineering department. James Liu (VP Engineering) is our primary contact. This pilot is critical for both product validation and fundraising (David Kim wants to see at least one paying pilot).

## Pilot Parameters
- Duration: 3 months
- Users: 50 engineers from Acme's platform team
- Pricing: $15/user/month (discounted from planned $25/user for pilot)
- Revenue: $750/month ($2,250 over pilot)
- Success criteria: >60% weekly active usage, NPS >40

## Requirements from James Liu
James outlined several enterprise requirements during our last call:

### Must Have
1. SSO/SAML integration with their Okta instance
2. Admin panel for user management and permissions
3. Data residency guarantee (US-only)
4. SOC 2 compliance roadmap (doesn't need to be certified yet)
5. API access for integration with their internal tools

### Nice to Have
1. Custom branding (Acme logo in the workspace)
2. Audit logging for compliance
3. Bulk import from their current Confluence instance
4. Slack integration for notifications

## Implementation Plan

### Phase 1: Core Setup (Week 1-2)
- Deploy dedicated Nexus instance for Acme
- Implement basic SSO/SAML (Priya Patel to handle)
- Set up admin panel (Sarah Chen)
- Data residency configuration

### Phase 2: Onboarding (Week 3)
- Create onboarding materials and guides
- Train Acme's IT admin on the platform
- Migrate sample content from Confluence
- Set up support channel

### Phase 3: Active Pilot (Week 4-12)
- Weekly check-ins with James Liu
- Usage monitoring and analytics
- Iterative improvements based on feedback
- Gather testimonials and case study data

## Risks
- SSO/SAML implementation complexity (Priya estimates 2 weeks)
- Confluence migration could be messy (unstructured data)
- 50 users might expose scalability issues (Sarah to run load tests)
- Timeline pressure from fundraising (David wants to reference this)

## Notes from Last James Liu Call
James is enthusiastic but cautious. His team currently uses a mix of Confluence, Slack, and Linear. The biggest pain point is context switching — exactly what Nexus solves. He mentioned that if the pilot goes well, they'd expand to their full 200-person eng team, which would be ~$5K/month at standard pricing.

James also asked about our roadmap for AI features. He's seen competitors adding AI summarization and was curious about our plans. I told him it's on our roadmap for Q3 but kept details vague since we're still exploring the approach. Need to follow up and schedule the demo.""",
            "frontmatter": json.dumps({"type": "project", "status": "active", "project": "Enterprise Pilot"}),
            "outgoing_links": json.dumps(["projects/nexus-mvp-spec.md", "projects/fundraising-tracker.md"]),
            "is_bookmarked": False,
            "created_at": ts(-15),
            "updated_at": ts(-8),
        },
        {
            "id": str(NOTE_IDS["daily-apr-7"]),
            "user_id": str(USER_ID),
            "file_path": "journal/daily-apr-7.md",
            "title": "Daily Journal - April 7",
            "content": """# Daily Journal — April 7

## Morning
Started the day with the team standup. Good energy from the team. Priya's auth work is progressing fast — she's on track to finish the full auth flow by end of week. Marcus showed the updated dashboard designs and they look fantastic. Sarah's infrastructure work is solid as always.

Feeling good about the Nexus MVP timeline. If we keep this pace, we should have a demo-ready product for David Kim within two weeks. That's the critical milestone for the fundraising round.

## Afternoon
Spent two hours refining the pitch deck based on Emma Thompson's feedback. She's right that we should lead with the story — the current deck jumps into features too quickly. Rewrote the opening three slides to focus on the "tool fragmentation" problem. Much stronger now.

Had a quick Slack exchange with David Kim — he sent a link to a TechCrunch article about collaboration tool fatigue. Good sign that he's thinking about our space. Replied with our perspective and mentioned we'd have the demo ready soon.

Also reviewed Anika Sharma's first draft of the "Why Your Team's Tools Don't Talk" blog post. The core argument is strong but it needs more concrete examples. Sent her feedback with suggestions to include specific workflow breakdowns.

## Evening Reflection
Three things that went well today:
1. Team standup was focused and productive (30 min, no tangents)
2. Pitch deck rewrites feel much stronger
3. David Kim engagement is a positive signal

Two things to improve:
1. Need to schedule the demo for James Liu at Acme — been putting this off
2. Should block more deep work time, too many context switches today

Top priorities for tomorrow:
- Review Priya's auth PR (she specifically asked for feedback on token rotation)
- Finalize the pricing page copy with Anika
- Start preparing materials for the Acme Corp demo""",
            "frontmatter": json.dumps({"type": "journal", "date": date_str()}),
            "outgoing_links": json.dumps(["meetings/team-standup-apr-7.md", "projects/fundraising-tracker.md"]),
            "is_bookmarked": False,
            "created_at": ts(0, -6),
            "updated_at": ts(0, -1),
        },
        {
            "id": str(NOTE_IDS["daily-apr-6"]),
            "user_id": str(USER_ID),
            "file_path": "journal/daily-apr-6.md",
            "title": "Daily Journal - April 6",
            "content": """# Daily Journal — April 6

## Morning
Deep work session on the product roadmap. Mapped out the feature prioritization for the next 8 weeks. The key tension is between building features for the Acme Corp enterprise pilot (SSO, admin panel, audit logs) vs. features that would impress investors in the demo (real-time collaboration, slick UX).

Decided to thread the needle: prioritize features that serve both audiences. The real-time collaboration demo is impressive for investors AND useful for Acme's team. SSO is a must-have for enterprise but also signals maturity to investors. The admin panel can wait until after the demo.

## Afternoon
Call with Emma Thompson about the marketing strategy. She's really pushing us toward a product-led growth model. Her argument: developer tools that succeed (Figma, Linear, Notion) all let users experience the product before buying. She wants us to have a free tier ready by launch.

I agree with the PLG approach in principle but worried about the engineering cost. Discussed with Sarah Chen after the call — she thinks we can do a limited free tier (3 users, 1 workspace) without much additional work since the billing system isn't built yet anyway. Good point.

Emma also connected me with Anika Sharma for content writing. Anika has a great portfolio — she wrote technical content for Vercel and Supabase. Her style is exactly what we need: clear, opinionated, developer-friendly. Set up an intro call for next week.

## Evening
Reviewed Marcus Rivera's latest design explorations for the brand identity. He's been experimenting with a geometric logo concept — interconnected nodes forming the letter N. It's clever and ties into the "nexus" concept literally. The color palette has evolved too: he's moved away from the blue-heavy corporate look toward a warmer gradient (amber to coral) that feels more distinctive.

Marcus also mocked up the landing page with the new brand direction. It looks significantly better than what we have now. Need to coordinate with Anika and Emma to make sure the messaging matches the visual evolution.

Spent the last hour reviewing the competitive landscape notes. The competitor analysis shows clear gaps we can exploit — none of the major players have real-time collaboration that works across different content types (docs, diagrams, code). That's our wedge.""",
            "frontmatter": json.dumps({"type": "journal", "date": date_str(-1)}),
            "outgoing_links": json.dumps(["brainstorms/feature-prioritization.md", "brainstorms/brand-identity.md", "reference/competitor-analysis.md"]),
            "is_bookmarked": False,
            "created_at": ts(-1, -6),
            "updated_at": ts(-1, -1),
        },
        {
            "id": str(NOTE_IDS["weekly-reflection-w14"]),
            "user_id": str(USER_ID),
            "file_path": "journal/weekly-reflection-w14.md",
            "title": "Weekly Reflection - Week 14",
            "content": """# Weekly Reflection — Week 14

## Wins This Week
1. **Auth system 80% complete.** Priya Patel has been crushing it. OAuth2 is working, magic links are in progress. We'll have a fully functional auth flow by early next week. This unblocks the demo for David Kim.

2. **Design system overhaul.** Marcus Rivera's token-based design system is a game changer. Dark mode support is almost free now, and the component library is much more consistent. The dashboard redesign looks professional and polished.

3. **Investor momentum.** David Kim from KV Capital is clearly interested. He's engaging proactively (sending articles, asking questions). If we can deliver a compelling demo in 2 weeks, I think we have a strong shot at a term sheet.

4. **Content pipeline started.** Anika Sharma delivered her first draft and it's solid. Having a dedicated content writer frees up a lot of my time for product and fundraising work.

## Challenges
1. **Enterprise pilot timeline.** The Acme Corp pilot with James Liu is lagging. I keep pushing the demo scheduling. Need to commit to a date this week — it's been 15 days since our last meaningful interaction.

2. **Fundraising vs. building tension.** Every hour I spend on pitch decks and investor emails is an hour not spent on product. Need to find a better balance. Maybe block mornings for product, afternoons for fundraising?

3. **Team bandwidth.** We're a team of 4 trying to build an MVP, launch marketing, close a round, and run an enterprise pilot simultaneously. Something might need to give. Consider: should we push the Marketing Launch timeline back by 2 weeks?

4. **Stripe integration.** The payment provider decision was made 2 weeks ago but we haven't started the integration. It's not blocking the demo but it's blocking the enterprise pilot pricing.

## Key Metrics
- Waitlist signups: 247 (+47 this week, mostly from HN traffic)
- GitHub commits: 84 this week across the team
- NPS from alpha testers: Not yet measured (need to set up)
- Fundraising pipeline: 3 active conversations, 1 strong lead (David Kim)

## Next Week Priorities
1. Ship auth module (Priya)
2. Dashboard implementation start (Sarah + Marcus)
3. Schedule Acme Corp demo (me)
4. Update pitch deck for David (me)
5. Finalize blog post #1 (Anika)

## Personal Energy Check
Energy: 7/10. Excited about momentum but feeling the weight of wearing many hats. The team is strong and I trust them, which helps. Need to make sure I'm delegating effectively and not trying to be in every conversation.

Sleep and exercise have been inconsistent this week. Committing to morning runs Mon/Wed/Fri next week — the clarity after exercise is invaluable for decision-making.""",
            "frontmatter": json.dumps({"type": "journal", "date": date_str(-3), "week": 14}),
            "outgoing_links": json.dumps(["projects/nexus-mvp-spec.md", "projects/fundraising-tracker.md", "projects/enterprise-pilot-notes.md"]),
            "is_bookmarked": True,
            "created_at": ts(-3),
            "updated_at": ts(-3),
        },
        {
            "id": str(NOTE_IDS["payment-provider"]),
            "user_id": str(USER_ID),
            "file_path": "decisions/payment-provider.md",
            "title": "Decision: Payment Provider",
            "content": """# Decision: Payment Provider

## Status: DECIDED — Stripe

## Context
We need a payment provider for Nexus billing. This decision affects the enterprise pilot pricing (Acme Corp), the self-serve billing for the PLG model Emma Thompson is pushing, and the overall financial infrastructure.

## Options Evaluated

### Option A: Stripe
- Pros: Best API/DX, excellent documentation, strong ecosystem (Stripe Billing, Tax, Invoicing), SaaS-optimized features, great for metered billing
- Cons: Higher fees (2.9% + 30¢ per transaction), no built-in tax compliance for all jurisdictions
- Cost: ~$45/month at projected $1500 MRR in first 6 months

### Option B: Paddle
- Pros: Merchant of Record (handles tax compliance globally), lower total cost when tax compliance is factored in, good for international sales
- Cons: Less flexible API, slower iteration speed, fewer integration options, weaker metered billing support
- Cost: ~$75/month at same MRR (includes tax handling)

### Option C: Custom (direct bank integration)
- Pros: Lowest per-transaction cost, full control
- Cons: Massive engineering effort, compliance burden, PCI DSS requirements, would take months to build
- Cost: Engineering time > any savings

## Decision Rationale
Going with Stripe because:
1. **Developer experience matters for speed.** We can integrate Stripe in days, not weeks. Priya Patel estimated 3-4 days for full integration vs. 2 weeks for Paddle.
2. **Metered billing is important.** Our API rate limiting tiers map directly to Stripe's metered billing model.
3. **Enterprise invoicing.** Acme Corp and future enterprise customers will need proper invoicing — Stripe Invoicing handles this well.
4. **Team familiarity.** Both Priya and Sarah Chen have used Stripe before.

We'll reassess when we expand internationally and tax compliance becomes more complex (probably Series A timeframe).

## Implementation Plan
1. Set up Stripe test environment — Priya (this week)
2. Implement subscription billing for Pro/Enterprise tiers
3. Add metered billing for API usage tracking
4. Build billing dashboard in admin panel

## Decided By
Me, with input from Priya Patel and Sarah Chen.
Date: 2 weeks ago""",
            "frontmatter": json.dumps({"type": "decision", "status": "decided", "decided_date": date_str(-14)}),
            "outgoing_links": json.dumps(["projects/nexus-mvp-spec.md", "projects/enterprise-pilot-notes.md"]),
            "is_bookmarked": False,
            "created_at": ts(-14),
            "updated_at": ts(-14),
        },
        {
            "id": str(NOTE_IDS["target-market"]),
            "user_id": str(USER_ID),
            "file_path": "decisions/target-market.md",
            "title": "Decision: Target Market",
            "content": """# Decision: Target Market

## Status: DECIDED — Mid-Market First

## Context
We need to define our initial target market segment. This affects everything: pricing, features, marketing messaging, sales strategy, and fundraising narrative. Emma Thompson has been pushing us to get clear on this before the Marketing Launch.

## Options Evaluated

### Option A: SMB (Small Business, <50 employees)
- Pros: Large volume, faster sales cycles, product-led acquisition
- Cons: High churn, low ARPU ($10-20/user), heavy support needs relative to revenue, price-sensitive
- GTM: Self-serve, content marketing, freemium
- Example customer: 10-person dev agency

### Option B: Mid-Market (50-500 employees)
- Pros: Meaningful contract sizes ($5K-50K ARR), established enough to have real collaboration pain, willing to try new tools, faster decision-making than enterprise
- Cons: Need both self-serve AND sales-assist motions, feature expectations are higher
- GTM: PLG with sales overlay, targeted outreach, case studies
- Example customer: Acme Corp (200-person eng team)

### Option C: Enterprise (500+ employees)
- Pros: Large contract sizes ($100K+ ARR), sticky customers, good for fundraising narrative
- Cons: 6-12 month sales cycles, heavy compliance/security requirements (SOC2, HIPAA, FedRAMP), need dedicated sales team, feature demands can derail roadmap
- GTM: Direct sales, enterprise marketing, RFP processes
- Example customer: Fortune 500 company

## Decision Rationale
Going with Mid-Market because:
1. **Acme Corp validates the segment.** James Liu's team (200 engineers) is exactly mid-market, and they have the collaboration pain we solve.
2. **Balanced unit economics.** $5K-50K ARR per customer is meaningful enough to build a business but doesn't require an enterprise sales team.
3. **PLG + Sales hybrid.** Emma Thompson's PLG strategy works here — let teams try for free, then upsell to paid when they hit limits.
4. **Fundraising narrative.** David Kim at KV Capital specifically mentioned that mid-market focus is a sweet spot for seed-stage companies.
5. **Feature scope is manageable.** Mid-market wants polished UX and core integrations. They don't need FedRAMP or custom deployment options (yet).

We'll expand upmarket (enterprise) and downmarket (SMB) as we scale, but mid-market is the beachhead.

## Implications
- Pricing: $15-25/user/month (aligns with Acme pilot pricing)
- Features: Focus on team collaboration, integrations, basic admin. No SOC2/HIPAA yet.
- Marketing: Developer-focused content, case studies from pilot customers
- Sales: Product-led with light sales touch for accounts >$5K ARR

## Decided By
Me, with input from Emma Thompson and David Kim's feedback.
Date: 3 weeks ago""",
            "frontmatter": json.dumps({"type": "decision", "status": "decided", "decided_date": date_str(-21)}),
            "outgoing_links": json.dumps(["projects/marketing-plan.md", "projects/enterprise-pilot-notes.md"]),
            "is_bookmarked": False,
            "created_at": ts(-21),
            "updated_at": ts(-21),
        },
        {
            "id": str(NOTE_IDS["feature-prioritization"]),
            "user_id": str(USER_ID),
            "file_path": "brainstorms/feature-prioritization.md",
            "title": "Feature Prioritization",
            "content": """# Feature Prioritization — Q2

## Framework
Using a weighted scoring model: Impact (1-5) × Confidence (1-5) ÷ Effort (1-5) = Priority Score.
Impact considers both user value and business value (fundraising, pilot success).

## Priority Matrix

### Tier 1 — Must Ship (MVP)
| Feature | Impact | Confidence | Effort | Score | Owner |
|---------|--------|-----------|--------|-------|-------|
| Auth (OAuth + Magic Links) | 5 | 5 | 3 | 8.3 | Priya Patel |
| Dashboard + Workspace | 5 | 4 | 4 | 5.0 | Marcus/Sarah |
| Real-time Collaboration | 5 | 4 | 5 | 4.0 | Sarah Chen |
| REST API v1 | 4 | 5 | 3 | 6.7 | Priya Patel |
| Billing (Stripe) | 4 | 5 | 2 | 10.0 | Priya Patel |

### Tier 2 — Important (Post-MVP)
| Feature | Impact | Confidence | Effort | Score | Owner |
|---------|--------|-----------|--------|-------|-------|
| SSO/SAML | 4 | 4 | 4 | 4.0 | Priya |
| Admin Panel | 3 | 4 | 3 | 4.0 | Sarah |
| Slack Integration | 3 | 3 | 2 | 4.5 | TBD |
| Keyboard Shortcuts | 3 | 5 | 1 | 15.0 | Marcus |
| Dark Mode | 2 | 5 | 1 | 10.0 | Marcus |

### Tier 3 — Nice to Have (Q3+)
| Feature | Impact | Confidence | Effort | Score | Owner |
|---------|--------|-----------|--------|-------|-------|
| Mobile App | 4 | 3 | 5 | 2.4 | TBD |
| AI Summarization | 4 | 2 | 4 | 2.0 | TBD |
| Confluence Import | 3 | 3 | 4 | 2.3 | TBD |
| Custom Branding | 2 | 4 | 2 | 4.0 | Marcus |
| Audit Logging | 3 | 4 | 3 | 4.0 | TBD |

## Key Tensions

### Investor Demo vs. Enterprise Pilot
The features David Kim wants to see (real-time collab, polished UX) are different from what James Liu at Acme needs (SSO, admin panel). We're prioritizing the demo-ready features first because:
1. Fundraising has a tighter deadline (3 weeks)
2. The visual wow factor of real-time collaboration sells better than admin panels
3. SSO can be implemented after the demo but before the Acme pilot starts

### Build vs. Buy
For Slack integration, we're leaning toward using Slack's Bolt framework rather than building a custom integration. Priya estimates 2 days with Bolt vs. 1 week custom. The trade-off is less customization but much faster time to market.

### Mobile Decision
We decided to delay mobile to Q3. The reasoning: web usage data from competitors shows 85%+ of collaboration tool usage is on desktop. Mobile is for consumption, not creation. We'll build a responsive web view that works on tablets as an interim solution — Marcus is designing this as part of the dashboard work.

## Dependencies Map
- Billing depends on: Payment Provider decision (DONE — Stripe)
- SSO depends on: Auth module completion (Priya, ETA: this week)
- Admin Panel depends on: Auth + basic dashboard
- Enterprise Pilot depends on: Auth + SSO + Admin Panel
- Demo for David depends on: Auth + Dashboard + Real-time Collab""",
            "frontmatter": json.dumps({"type": "brainstorm", "project": "Nexus MVP"}),
            "outgoing_links": json.dumps(["projects/nexus-mvp-spec.md", "decisions/payment-provider.md"]),
            "is_bookmarked": False,
            "created_at": ts(-7),
            "updated_at": ts(-1),
        },
        {
            "id": str(NOTE_IDS["brand-identity"]),
            "user_id": str(USER_ID),
            "file_path": "brainstorms/brand-identity.md",
            "title": "Brand Identity Exploration",
            "content": """# Brand Identity Exploration

## Led by Marcus Rivera

## Brand Vision
Nexus should feel like a tool built by people who understand the pain of fragmented workflows. The brand should communicate: clarity, connection, and speed. We're not another corporate collaboration tool — we're the missing layer that makes existing tools work together.

## Logo Concepts

### Concept A: Connected Nodes (Current Favorite)
A geometric mark of three interconnected nodes forming the letter N. The nodes represent different tools/people coming together. Marcus presented three variants:
- Minimal: Clean lines, single weight — works well at small sizes
- Dynamic: Variable line weights suggesting data flow — more distinctive but harder to reproduce
- Abstract: Just the connection points, no explicit N — too ambiguous

Sarah Chen and I both gravitate toward the Minimal variant. It's clean, memorable, and works at favicon size. Marcus will refine this direction.

### Concept B: Waveform
An audio-waveform-inspired mark suggesting real-time activity. Interesting but doesn't communicate "collaboration" as clearly. Parking this.

### Concept C: Overlap
Overlapping circles (like a Venn diagram) representing the intersection of tools. Too similar to Mastercard/Olympics. Rejected.

## Color Palette

### Primary Palette
Marcus has moved away from the initial blue-heavy approach (too corporate, too similar to Slack/Linear) toward a warmer direction:
- Primary: Amber (#F59E0B) — warm, energetic, attention-grabbing
- Secondary: Coral (#F97316) — complementary to amber, good for CTAs
- Dark: Charcoal (#1F2937) — sophisticated, high contrast
- Light: Cream (#FDF8F0) — warm alternative to pure white

### Functional Colors
- Success: Emerald (#10B981)
- Warning: Amber (#F59E0B)
- Error: Rose (#F43F5E)
- Info: Sky (#0EA5E9)

Emma Thompson flagged that amber as primary is distinctive in the collaboration space but needs to be tested for accessibility. Marcus confirmed all color combinations pass WCAG AA contrast requirements.

## Typography
- Headings: Inter (geometric, clean, widely supported)
- Body: Inter (consistency, excellent readability at small sizes)
- Code/Mono: JetBrains Mono (developer audience will appreciate this)

## Voice & Tone Guidelines
Anika Sharma is building out the voice guidelines for content:
- **Clear over clever.** No jargon, no buzzwords. Say what you mean.
- **Confident, not arrogant.** We believe in our approach but acknowledge we're learning.
- **Technical but accessible.** Respect the audience's intelligence without assuming deep technical knowledge.
- **Warm but professional.** We're humans building for humans, but we're serious about quality.

Example: Instead of "Leverage our synergistic collaboration paradigm", write "Your tools work better when they talk to each other. Nexus makes that happen."

## Brand Applications
Marcus is creating brand application mockups:
1. Landing page (new design with amber/coral palette)
2. App UI (dashboard with new color tokens)
3. Email templates (onboarding sequence)
4. Social media templates (Twitter/LinkedIn)
5. Pitch deck template (updated for David Kim meeting)

## Next Steps
- Marcus to finalize logo (Minimal Connected Nodes variant)
- Update design tokens in component library to match new palette
- Anika to incorporate voice guidelines into blog drafts
- Emma to review brand positioning against competitor brands
- Share brand guidelines with the full team""",
            "frontmatter": json.dumps({"type": "brainstorm", "project": "Marketing Launch"}),
            "outgoing_links": json.dumps(["projects/marketing-plan.md", "meetings/design-review-q2.md"]),
            "is_bookmarked": False,
            "created_at": ts(-10),
            "updated_at": ts(-5),
        },
        {
            "id": str(NOTE_IDS["competitor-analysis"]),
            "user_id": str(USER_ID),
            "file_path": "reference/competitor-analysis.md",
            "title": "Competitor Analysis",
            "content": """# Competitor Analysis

## Market Landscape
The collaboration tools market is large ($47B) but fragmented. No single player owns the full workflow. This fragmentation IS the problem Nexus solves — and it's also our biggest challenge in positioning.

## Direct Competitors

### Notion
- **Strengths:** Beautiful UX, flexible blocks, strong template ecosystem, massive user base (30M+)
- **Weaknesses:** Real-time collaboration is clunky (noticeable lag), no true offline support, performance degrades with large workspaces, API is limited
- **Pricing:** Free for personal, $8/user/month for team, $15/user/month for business
- **Our edge:** Nexus's CRDT-based engine provides genuinely real-time collaboration. Sarah Chen's architecture handles conflicts gracefully where Notion's last-write-wins approach causes data loss.

### Coda
- **Strengths:** Powerful formulas, doc-as-app philosophy, good automation
- **Weaknesses:** Steep learning curve, less polished UX than Notion, smaller ecosystem
- **Pricing:** Free basic, $10/user/month for team, $30/user/month for enterprise
- **Our edge:** Nexus is simpler by design. We're a collaboration layer, not a spreadsheet replacement. Less powerful but more accessible.

### Linear
- **Strengths:** Best-in-class project management UX, keyboard-first design, fast performance
- **Weaknesses:** Narrow focus (issue tracking only), no document collaboration, limited to engineering teams
- **Pricing:** Free basic, $8/user/month for standard, custom enterprise
- **Our edge:** Nexus spans across project management, docs, and communication. Linear users would use Nexus alongside Linear, not instead of it.

### Slack
- **Strengths:** Ubiquitous, strong integrations ecosystem, real-time messaging
- **Weaknesses:** Information gets lost in channels, no structured knowledge management, terrible search, notification overload
- **Pricing:** Free basic, $7.25/user/month pro, $12.50/user/month business
- **Our edge:** Nexus captures the context from Slack conversations and makes it actionable. We integrate with Slack rather than compete with it.

## Indirect Competitors
- **Confluence:** Legacy, slow, but deeply embedded in enterprise. Acme Corp (James Liu) is migrating away from it.
- **Google Workspace:** Familiar but fragmented (Docs, Sheets, Slides are separate experiences)
- **Microsoft Teams/Loop:** Enterprise-focused, improving rapidly, but complex and heavyweight

## Our Differentiation (Key Messaging for Emma Thompson and Anika Sharma)
1. **Real-time by default.** Everything is collaborative from day one, not bolted on.
2. **Integration-first.** We don't replace your tools; we make them work together.
3. **Developer-friendly.** API-first design, keyboard shortcuts, extensibility.
4. **Performance.** Sub-50ms collaboration latency (most competitors are 200ms+).

## Gaps We Can Exploit
- **No one does cross-content-type collaboration well.** Notion does docs, Linear does issues, Figma does design. None of them let you collaborate across these boundaries in real-time.
- **Offline-first is rare.** Most tools require constant connectivity. Our CRDT approach enables true offline support.
- **Mid-market is underserved.** Enterprise tools are too complex, SMB tools are too simple. The 50-500 employee segment (our target, per market decision) lacks a purpose-built solution.

## Competitive Risk Assessment
- **Notion adding better real-time:** Medium risk. Hard to retrofit CRDTs into an existing architecture.
- **Slack acquiring a doc tool:** Medium risk. They tried with Canvas and it's mediocre.
- **Microsoft Loop maturing:** High risk long-term, but their pace is slow and enterprise-focused.
- **New entrant with AI-first approach:** Medium risk. AI features are complementary, not core. We'll add AI in Q3.

David Kim specifically asked about competitive differentiation during our investor call. This analysis formed the basis of our pitch deck slide. Need to keep this updated as the landscape evolves.""",
            "frontmatter": json.dumps({"type": "reference", "topic": "competitive analysis"}),
            "outgoing_links": json.dumps(["decisions/target-market.md", "projects/marketing-plan.md"]),
            "is_bookmarked": True,
            "created_at": ts(-25),
            "updated_at": ts(-5),
        },
    ]
    for n in notes:
        await conn.execute(text("""
            INSERT INTO vault_notes (id, user_id, file_path, title, content, frontmatter,
                                     outgoing_links, is_bookmarked, created_at, updated_at)
            VALUES (:id, :user_id, :file_path, :title, :content, :frontmatter::jsonb,
                    :outgoing_links::jsonb, :is_bookmarked, :created_at, :updated_at)
            ON CONFLICT DO NOTHING
        """), n)


async def insert_action_items(conn):
    print("  Inserting action items...")
    actions = [
        {
            "id": str(ACTION_IDS[0]),
            "user_id": str(USER_ID),
            "note_id": str(NOTE_IDS["marketing-plan"]),
            "task": "Finalize pricing page copy",
            "assignee": "Anika Sharma",
            "deadline": date_str(1),
            "priority": "high",
            "status": "pending",
            "created_at": ts(-2),
        },
        {
            "id": str(ACTION_IDS[1]),
            "user_id": str(USER_ID),
            "note_id": str(NOTE_IDS["fundraising-tracker"]),
            "task": "Send investor update to David",
            "assignee": None,
            "deadline": date_str(3),
            "priority": "high",
            "status": "pending",
            "created_at": ts(-3),
        },
        {
            "id": str(ACTION_IDS[2]),
            "user_id": str(USER_ID),
            "note_id": str(NOTE_IDS["nexus-mvp-spec"]),
            "task": "Review Priya's authentication PR",
            "assignee": None,
            "deadline": date_str(0),
            "priority": "high",
            "status": "pending",
            "created_at": ts(-1),
        },
        {
            "id": str(ACTION_IDS[3]),
            "user_id": str(USER_ID),
            "note_id": str(NOTE_IDS["enterprise-pilot-notes"]),
            "task": "Schedule demo for James at Acme",
            "assignee": None,
            "deadline": date_str(-2),
            "priority": "medium",
            "status": "pending",
            "created_at": ts(-5),
        },
        {
            "id": str(ACTION_IDS[4]),
            "user_id": str(USER_ID),
            "note_id": str(NOTE_IDS["brand-identity"]),
            "task": "Update brand guidelines document",
            "assignee": "Marcus Rivera",
            "deadline": date_str(5),
            "priority": "medium",
            "status": "pending",
            "created_at": ts(-3),
        },
        {
            "id": str(ACTION_IDS[5]),
            "user_id": str(USER_ID),
            "note_id": str(NOTE_IDS["payment-provider"]),
            "task": "Set up Stripe test environment",
            "assignee": None,
            "deadline": date_str(7),
            "priority": "medium",
            "status": "completed",
            "created_at": ts(-10),
        },
        {
            "id": str(ACTION_IDS[6]),
            "user_id": str(USER_ID),
            "note_id": str(NOTE_IDS["marketing-plan"]),
            "task": "Draft blog post for launch",
            "assignee": "Emma Thompson",
            "deadline": date_str(10),
            "priority": "low",
            "status": "pending",
            "created_at": ts(-5),
        },
        {
            "id": str(ACTION_IDS[7]),
            "user_id": str(USER_ID),
            "note_id": str(NOTE_IDS["fundraising-tracker"]),
            "task": "Prepare seed deck revisions",
            "assignee": None,
            "deadline": date_str(5),
            "priority": "high",
            "status": "pending",
            "created_at": ts(-4),
        },
        {
            "id": str(ACTION_IDS[8]),
            "user_id": str(USER_ID),
            "note_id": str(NOTE_IDS["nexus-mvp-spec"]),
            "task": "Run load tests on API",
            "assignee": "Priya Patel",
            "deadline": date_str(4),
            "priority": "medium",
            "status": "pending",
            "created_at": ts(-2),
        },
        {
            "id": str(ACTION_IDS[9]),
            "user_id": str(USER_ID),
            "note_id": str(NOTE_IDS["nexus-mvp-spec"]),
            "task": "Create onboarding flow wireframes",
            "assignee": "Marcus Rivera",
            "deadline": date_str(6),
            "priority": "medium",
            "status": "completed",
            "created_at": ts(-8),
        },
    ]
    for a in actions:
        await conn.execute(text("""
            INSERT INTO action_items (id, user_id, note_id, task, assignee, deadline,
                                      priority, status, created_at)
            VALUES (:id, :user_id, :note_id, :task, :assignee, :deadline,
                    :priority, :status, :created_at)
            ON CONFLICT DO NOTHING
        """), a)


async def insert_calendar_events(conn):
    print("  Inserting calendar events...")
    events = [
        {
            "id": str(CALENDAR_IDS[0]),
            "user_id": str(USER_ID),
            "note_id": str(NOTE_IDS["team-standup-apr-7"]),
            "title": "Team Standup",
            "event_date": date_str(0),
            "event_type": "meeting",
            "description": "Daily standup with Sarah, Priya, and Marcus. Review progress on Nexus MVP.",
            "created_at": ts(-7),
        },
        {
            "id": str(CALENDAR_IDS[1]),
            "user_id": str(USER_ID),
            "note_id": str(NOTE_IDS["investor-call-david"]),
            "title": "Investor Call - David Kim",
            "event_date": date_str(2),
            "event_type": "meeting",
            "description": "Follow-up call with David Kim at KV Capital. Discuss demo timeline and term sheet.",
            "created_at": ts(-5),
        },
        {
            "id": str(CALENDAR_IDS[2]),
            "user_id": str(USER_ID),
            "note_id": str(NOTE_IDS["design-review-q2"]),
            "title": "Design Review Q2",
            "event_date": date_str(3),
            "event_type": "meeting",
            "description": "Q2 design review with Marcus Rivera and Sarah Chen. Review dashboard and brand updates.",
            "created_at": ts(-3),
        },
        {
            "id": str(CALENDAR_IDS[3]),
            "user_id": str(USER_ID),
            "note_id": str(NOTE_IDS["enterprise-pilot-notes"]),
            "title": "Acme Corp Demo",
            "event_date": date_str(5),
            "event_type": "meeting",
            "description": "Product demo for James Liu and Acme Corp engineering team. Focus on real-time collaboration and SSO.",
            "created_at": ts(-2),
        },
        {
            "id": str(CALENDAR_IDS[4]),
            "user_id": str(USER_ID),
            "note_id": str(NOTE_IDS["marketing-plan"]),
            "title": "Content Sync with Anika",
            "event_date": date_str(4),
            "event_type": "reminder",
            "description": "Review Anika Sharma's blog post drafts and align on pricing page copy.",
            "created_at": ts(-1),
        },
        {
            "id": str(CALENDAR_IDS[5]),
            "user_id": str(USER_ID),
            "note_id": str(NOTE_IDS["nexus-mvp-spec"]),
            "title": "Sprint Planning",
            "event_date": date_str(7),
            "event_type": "meeting",
            "description": "Sprint planning for the next 2-week cycle. Prioritize features for demo readiness.",
            "created_at": ts(-1),
        },
    ]
    for e in events:
        await conn.execute(text("""
            INSERT INTO calendar_events (id, user_id, note_id, title, event_date,
                                         event_type, description, created_at)
            VALUES (:id, :user_id, :note_id, :title, :event_date,
                    :event_type, :description, :created_at)
            ON CONFLICT DO NOTHING
        """), e)


async def insert_decisions(conn):
    print("  Inserting decisions...")
    decisions = [
        {
            "id": str(DECISION_IDS[0]),
            "user_id": str(USER_ID),
            "title": "Use Stripe for payments",
            "description": "Selected Stripe as payment provider for Nexus billing, subscriptions, and enterprise invoicing.",
            "reasoning": "Stripe offers the best developer experience, metered billing support, and enterprise invoicing. Priya estimated 3-4 day integration vs. 2 weeks for Paddle. Team has prior Stripe experience. 2.9% + 30c per transaction is acceptable at current scale. Will reassess for international tax compliance at Series A.",
            "alternatives": "Paddle (Merchant of Record, handles tax but less flexible API), Custom bank integration (lowest cost but months of engineering, PCI compliance burden)",
            "status": "active",
            "decided_at": date_str(-14),
            "revisit_date": date_str(180),
            "created_at": ts(-14),
        },
        {
            "id": str(DECISION_IDS[1]),
            "user_id": str(USER_ID),
            "title": "Target mid-market first",
            "description": "Focus on 50-500 employee companies as initial target market for Nexus.",
            "reasoning": "Mid-market offers balanced unit economics ($5K-50K ARR per customer) without the long sales cycles of enterprise. Acme Corp pilot validates the segment. PLG + sales-assist motion works well here. David Kim at KV Capital confirmed mid-market focus is a sweet spot for seed-stage. Emma Thompson's marketing strategy aligns with this segment.",
            "alternatives": "SMB (<50 employees) - high volume but high churn and low ARPU. Enterprise (500+) - large contracts but 6-12 month sales cycles, heavy compliance requirements, needs dedicated sales team",
            "status": "active",
            "decided_at": date_str(-21),
            "revisit_date": date_str(90),
            "created_at": ts(-21),
        },
        {
            "id": str(DECISION_IDS[2]),
            "user_id": str(USER_ID),
            "title": "Hire freelance designer",
            "description": "Bring on Anika Sharma as freelance content writer rather than hiring full-time.",
            "reasoning": "At our current stage, a freelance content writer gives us flexibility without the commitment of a full-time hire. Anika's portfolio (Vercel, Supabase) is exactly our target audience. Emma Thompson recommended the freelance approach until we validate content as a channel. Budget impact: $3K for initial content batch vs. $6-8K/month for full-time.",
            "alternatives": "Full-time content hire ($6-8K/month plus equity, better alignment but higher burn rate and harder to reverse). Agency ($5-10K/month, less context but more output capacity). DIY (free but founder time is the most expensive resource)",
            "status": "active",
            "decided_at": date_str(-7),
            "revisit_date": date_str(60),
            "created_at": ts(-7),
        },
        {
            "id": str(DECISION_IDS[3]),
            "user_id": str(USER_ID),
            "title": "Delay mobile app to Q3",
            "description": "Focus on web-first experience, delay dedicated mobile app to Q3 2025.",
            "reasoning": "Competitor usage data shows 85%+ of collaboration tool usage on desktop. Mobile is consumption-focused, not creation-focused. Marcus is designing responsive layouts (768px+) as interim solution. Mobile development would require React Native expertise we don't have in-house. Better to nail the desktop experience first — that's what will win the demo for David Kim and the Acme pilot with James Liu.",
            "alternatives": "Build mobile alongside web (doubles engineering scope, delays MVP by 4-6 weeks). Mobile-first (contrarian approach, but our target users work primarily on desktop). Progressive Web App (middle ground, but push notifications and offline are limited on iOS)",
            "status": "active",
            "decided_at": date_str(-10),
            "revisit_date": date_str(75),
            "created_at": ts(-10),
        },
    ]
    for d in decisions:
        await conn.execute(text("""
            INSERT INTO vault_decisions (id, user_id, title, description, reasoning,
                                         alternatives, status, decided_at, revisit_date, created_at)
            VALUES (:id, :user_id, :title, :description, :reasoning,
                    :alternatives, :status, :decided_at, :revisit_date, :created_at)
            ON CONFLICT DO NOTHING
        """), d)


async def insert_context_events(conn):
    print("  Inserting context events...")
    events = [
        # Email events
        {
            "id": str(CONTEXT_EVENT_IDS[0]),
            "user_id": str(USER_ID),
            "source": "email",
            "source_id": "email-001",
            "event_type": "email_received",
            "content": "David Kim sent a follow-up email after our last investor call. He's shared the TechCrunch article about collaboration tool fatigue and wants to discuss how Nexus fits into the trend. He also asked for the updated pitch deck.",
            "structured_data": json.dumps({"from": "david@kv-capital.com", "subject": "Re: Nexus - collaboration market trends", "thread_id": "thread-dk-001"}),
            "timestamp": ts(-2),
            "extracted_entities": json.dumps([{"type": "person", "value": "David Kim"}, {"type": "organization", "value": "KV Capital"}]),
            "extracted_people": ["David Kim"],
            "topics": ["fundraising", "investor relations", "market trends"],
            "action_items": json.dumps([{"task": "Send updated pitch deck to David", "priority": "high"}]),
            "tier0_at": ts(-2),
            "tier1_at": ts(-1.5),
            "tier2_at": None,
            "created_at": ts(-2),
        },
        {
            "id": str(CONTEXT_EVENT_IDS[1]),
            "user_id": str(USER_ID),
            "source": "email",
            "source_id": "email-002",
            "event_type": "email_received",
            "content": "James Liu from Acme Corp replied to our pilot proposal. He's confirmed the 50-user trial with his platform engineering team. He needs SSO/SAML integration with their Okta instance as a prerequisite. Asking about timeline.",
            "structured_data": json.dumps({"from": "james@acmecorp.com", "subject": "Re: Nexus Pilot - Acme Corp", "thread_id": "thread-jl-001"}),
            "timestamp": ts(-15),
            "extracted_entities": json.dumps([{"type": "person", "value": "James Liu"}, {"type": "organization", "value": "Acme Corp"}]),
            "extracted_people": ["James Liu"],
            "topics": ["enterprise pilot", "SSO", "Acme Corp"],
            "action_items": json.dumps([{"task": "Confirm pilot timeline with James", "priority": "high"}]),
            "tier0_at": ts(-15),
            "tier1_at": ts(-14),
            "tier2_at": ts(-7),
            "created_at": ts(-15),
        },
        {
            "id": str(CONTEXT_EVENT_IDS[2]),
            "user_id": str(USER_ID),
            "source": "email",
            "source_id": "email-003",
            "event_type": "email_received",
            "content": "Emma Thompson shared her feedback on the pitch deck v3. Key points: lead with problem story, add competitive landscape slide, include Acme Corp pilot as social proof, move technical slides to appendix.",
            "structured_data": json.dumps({"from": "emma@growthlab.co", "subject": "Pitch deck feedback - v3", "thread_id": "thread-et-001"}),
            "timestamp": ts(-8),
            "extracted_entities": json.dumps([{"type": "person", "value": "Emma Thompson"}, {"type": "organization", "value": "GrowthLab"}]),
            "extracted_people": ["Emma Thompson"],
            "topics": ["fundraising", "pitch deck", "marketing strategy"],
            "action_items": json.dumps([{"task": "Incorporate Emma's pitch deck feedback", "priority": "medium"}]),
            "tier0_at": ts(-8),
            "tier1_at": ts(-7),
            "tier2_at": None,
            "created_at": ts(-8),
        },
        {
            "id": str(CONTEXT_EVENT_IDS[3]),
            "user_id": str(USER_ID),
            "source": "email",
            "source_id": "email-004",
            "event_type": "email_received",
            "content": "Anika Sharma sent first draft of 'Why Your Team Tools Don't Talk to Each Other' blog post. Draft is 1500 words. Core argument is strong but needs more concrete workflow examples.",
            "structured_data": json.dumps({"from": "anika@freelance.dev", "subject": "Draft: Why Your Team's Tools Don't Talk", "thread_id": "thread-as-001"}),
            "timestamp": ts(-4),
            "extracted_entities": json.dumps([{"type": "person", "value": "Anika Sharma"}]),
            "extracted_people": ["Anika Sharma"],
            "topics": ["content marketing", "blog post", "marketing launch"],
            "action_items": json.dumps([{"task": "Review Anika's blog draft and provide feedback", "priority": "medium"}]),
            "tier0_at": ts(-4),
            "tier1_at": ts(-3),
            "tier2_at": None,
            "created_at": ts(-4),
        },
        # Slack events
        {
            "id": str(CONTEXT_EVENT_IDS[4]),
            "user_id": str(USER_ID),
            "source": "slack",
            "source_id": "slack-001",
            "event_type": "message",
            "content": "Sarah Chen in #engineering: 'Stress test results are in. We can handle 10k concurrent WebSocket connections with <50ms latency. NATS is working great as the message broker. Going to document the architecture for the investor deck.'",
            "structured_data": json.dumps({"channel": "#engineering", "thread_ts": "1712000000.000100"}),
            "timestamp": ts(-3),
            "extracted_entities": json.dumps([{"type": "person", "value": "Sarah Chen"}, {"type": "technology", "value": "NATS"}, {"type": "technology", "value": "WebSocket"}]),
            "extracted_people": ["Sarah Chen"],
            "topics": ["infrastructure", "performance", "real-time collaboration"],
            "action_items": None,
            "tier0_at": ts(-3),
            "tier1_at": ts(-2.5),
            "tier2_at": None,
            "created_at": ts(-3),
        },
        {
            "id": str(CONTEXT_EVENT_IDS[5]),
            "user_id": str(USER_ID),
            "source": "slack",
            "source_id": "slack-002",
            "event_type": "message",
            "content": "Priya Patel in #engineering: 'Auth PR is up! OAuth2 with Google and GitHub working. Magic link flow in progress. Would love a review on the token rotation logic - it's the trickiest part.'",
            "structured_data": json.dumps({"channel": "#engineering", "thread_ts": "1712100000.000200"}),
            "timestamp": ts(-1),
            "extracted_entities": json.dumps([{"type": "person", "value": "Priya Patel"}, {"type": "technology", "value": "OAuth2"}]),
            "extracted_people": ["Priya Patel"],
            "topics": ["authentication", "code review", "Nexus MVP"],
            "action_items": json.dumps([{"task": "Review auth PR", "priority": "high"}]),
            "tier0_at": ts(-1),
            "tier1_at": ts(-0.5),
            "tier2_at": None,
            "created_at": ts(-1),
        },
        {
            "id": str(CONTEXT_EVENT_IDS[6]),
            "user_id": str(USER_ID),
            "source": "slack",
            "source_id": "slack-003",
            "event_type": "message",
            "content": "Marcus Rivera in #design: 'New dashboard wireframes are ready for review! Key changes: collapsible sidebar, keyboard shortcuts, activity feed component. Also sharing the new icon set. Check the Figma link.'",
            "structured_data": json.dumps({"channel": "#design", "thread_ts": "1712050000.000300"}),
            "timestamp": ts(-2),
            "extracted_entities": json.dumps([{"type": "person", "value": "Marcus Rivera"}]),
            "extracted_people": ["Marcus Rivera"],
            "topics": ["design", "dashboard", "UX", "Nexus MVP"],
            "action_items": json.dumps([{"task": "Review dashboard wireframes", "priority": "medium"}]),
            "tier0_at": ts(-2),
            "tier1_at": ts(-1.5),
            "tier2_at": None,
            "created_at": ts(-2),
        },
        {
            "id": str(CONTEXT_EVENT_IDS[7]),
            "user_id": str(USER_ID),
            "source": "slack",
            "source_id": "slack-004",
            "event_type": "message",
            "content": "Sarah Chen in #general: 'Quick heads up - I chatted with David Kim via email about our architecture. He's really interested in the CRDT approach. I'll prep a one-page tech architecture doc for his reference.'",
            "structured_data": json.dumps({"channel": "#general", "thread_ts": "1712110000.000400"}),
            "timestamp": ts(-2, -3),
            "extracted_entities": json.dumps([{"type": "person", "value": "Sarah Chen"}, {"type": "person", "value": "David Kim"}, {"type": "technology", "value": "CRDT"}]),
            "extracted_people": ["Sarah Chen", "David Kim"],
            "topics": ["investor relations", "technical architecture", "fundraising"],
            "action_items": None,
            "tier0_at": ts(-2, -3),
            "tier1_at": ts(-2),
            "tier2_at": None,
            "created_at": ts(-2, -3),
        },
        {
            "id": str(CONTEXT_EVENT_IDS[8]),
            "user_id": str(USER_ID),
            "source": "slack",
            "source_id": "slack-005",
            "event_type": "message",
            "content": "Priya Patel in #engineering: 'API rate limiting is implemented. Three tiers: free (100/min), pro (1000/min), enterprise (10k/min). Using Redis for the sliding window counter. Tests passing.'",
            "structured_data": json.dumps({"channel": "#engineering", "thread_ts": "1711900000.000500"}),
            "timestamp": ts(-5),
            "extracted_entities": json.dumps([{"type": "person", "value": "Priya Patel"}, {"type": "technology", "value": "Redis"}]),
            "extracted_people": ["Priya Patel"],
            "topics": ["API", "rate limiting", "backend", "Nexus MVP"],
            "action_items": None,
            "tier0_at": ts(-5),
            "tier1_at": ts(-4),
            "tier2_at": None,
            "created_at": ts(-5),
        },
        # GitHub events
        {
            "id": str(CONTEXT_EVENT_IDS[9]),
            "user_id": str(USER_ID),
            "source": "github",
            "source_id": "pr-042",
            "event_type": "pr_merged",
            "content": "PR #42 merged: 'feat: implement OAuth2 authentication with Google and GitHub providers'. Added OAuth2 flow, secure token storage, session management with JWT, and automatic token rotation.",
            "structured_data": json.dumps({"repo": "nexus-app/nexus", "pr_number": 42, "author": "priya-patel", "additions": 1247, "deletions": 89}),
            "timestamp": ts(-1, -4),
            "extracted_entities": json.dumps([{"type": "person", "value": "Priya Patel"}, {"type": "technology", "value": "OAuth2"}]),
            "extracted_people": ["Priya Patel"],
            "topics": ["authentication", "OAuth2", "security", "Nexus MVP"],
            "action_items": None,
            "tier0_at": ts(-1, -4),
            "tier1_at": ts(-1),
            "tier2_at": None,
            "created_at": ts(-1, -4),
        },
        {
            "id": str(CONTEXT_EVENT_IDS[10]),
            "user_id": str(USER_ID),
            "source": "github",
            "source_id": "pr-038",
            "event_type": "pr_merged",
            "content": "PR #38 merged: 'feat: CRDT-based real-time collaboration engine'. Implemented Yjs integration for concurrent editing, cursor presence, and offline sync. WebSocket transport layer with NATS message broker.",
            "structured_data": json.dumps({"repo": "nexus-app/nexus", "pr_number": 38, "author": "sarah-chen", "additions": 3421, "deletions": 156}),
            "timestamp": ts(-7),
            "extracted_entities": json.dumps([{"type": "person", "value": "Sarah Chen"}, {"type": "technology", "value": "CRDT"}, {"type": "technology", "value": "Yjs"}, {"type": "technology", "value": "NATS"}]),
            "extracted_people": ["Sarah Chen"],
            "topics": ["real-time collaboration", "CRDT", "infrastructure", "Nexus MVP"],
            "action_items": None,
            "tier0_at": ts(-7),
            "tier1_at": ts(-6),
            "tier2_at": ts(-3),
            "created_at": ts(-7),
        },
        {
            "id": str(CONTEXT_EVENT_IDS[11]),
            "user_id": str(USER_ID),
            "source": "github",
            "source_id": "pr-040",
            "event_type": "pr_merged",
            "content": "PR #40 merged: 'feat: dashboard layout system with workspace presets'. Three layout presets (Focus, Split, Command Center) with drag-and-drop panel management. Responsive from 768px up.",
            "structured_data": json.dumps({"repo": "nexus-app/nexus", "pr_number": 40, "author": "sarah-chen", "additions": 2104, "deletions": 345}),
            "timestamp": ts(-4),
            "extracted_entities": json.dumps([{"type": "person", "value": "Sarah Chen"}, {"type": "person", "value": "Marcus Rivera"}]),
            "extracted_people": ["Sarah Chen", "Marcus Rivera"],
            "topics": ["dashboard", "UX", "frontend", "Nexus MVP"],
            "action_items": None,
            "tier0_at": ts(-4),
            "tier1_at": ts(-3),
            "tier2_at": None,
            "created_at": ts(-4),
        },
        {
            "id": str(CONTEXT_EVENT_IDS[12]),
            "user_id": str(USER_ID),
            "source": "github",
            "source_id": "pr-035",
            "event_type": "pr_merged",
            "content": "PR #35 merged: 'feat: API rate limiting with Redis sliding window'. Implemented tiered rate limiting for free, pro, and enterprise plans. Redis-backed sliding window counter with configurable limits per API key.",
            "structured_data": json.dumps({"repo": "nexus-app/nexus", "pr_number": 35, "author": "priya-patel", "additions": 567, "deletions": 23}),
            "timestamp": ts(-10),
            "extracted_entities": json.dumps([{"type": "person", "value": "Priya Patel"}, {"type": "technology", "value": "Redis"}]),
            "extracted_people": ["Priya Patel"],
            "topics": ["API", "rate limiting", "Redis", "backend"],
            "action_items": None,
            "tier0_at": ts(-10),
            "tier1_at": ts(-9),
            "tier2_at": ts(-5),
            "created_at": ts(-10),
        },
        {
            "id": str(CONTEXT_EVENT_IDS[13]),
            "user_id": str(USER_ID),
            "source": "github",
            "source_id": "pr-030",
            "event_type": "pr_merged",
            "content": "PR #30 merged: 'infra: Kubernetes cluster setup with auto-scaling'. EKS cluster configuration, Terraform modules, GitHub Actions CI/CD pipeline. Auto-scaling policies for WebSocket server pods.",
            "structured_data": json.dumps({"repo": "nexus-app/nexus-infra", "pr_number": 30, "author": "sarah-chen", "additions": 1890, "deletions": 0}),
            "timestamp": ts(-14),
            "extracted_entities": json.dumps([{"type": "person", "value": "Sarah Chen"}, {"type": "technology", "value": "Kubernetes"}, {"type": "technology", "value": "Terraform"}]),
            "extracted_people": ["Sarah Chen"],
            "topics": ["infrastructure", "Kubernetes", "DevOps", "Nexus MVP"],
            "action_items": None,
            "tier0_at": ts(-14),
            "tier1_at": ts(-13),
            "tier2_at": ts(-7),
            "created_at": ts(-14),
        },
        # Calendar events (context)
        {
            "id": str(CONTEXT_EVENT_IDS[14]),
            "user_id": str(USER_ID),
            "source": "calendar",
            "source_id": "cal-001",
            "event_type": "meeting",
            "content": "Team standup with Sarah Chen, Priya Patel, and Marcus Rivera. Discussed auth progress, dashboard designs, and infrastructure updates. Key outcome: demo timeline confirmed for 2 weeks.",
            "structured_data": json.dumps({"calendar": "primary", "attendees": ["sarah@nexus.io", "priya@nexus.io", "marcus@nexus.io"], "duration_minutes": 30}),
            "timestamp": ts(-1),
            "extracted_entities": json.dumps([{"type": "person", "value": "Sarah Chen"}, {"type": "person", "value": "Priya Patel"}, {"type": "person", "value": "Marcus Rivera"}]),
            "extracted_people": ["Sarah Chen", "Priya Patel", "Marcus Rivera"],
            "topics": ["standup", "team sync", "Nexus MVP"],
            "action_items": json.dumps([{"task": "Review Priya's auth PR"}, {"task": "Sarah to prepare tech doc for David"}]),
            "tier0_at": ts(-1),
            "tier1_at": ts(-0.5),
            "tier2_at": None,
            "created_at": ts(-1),
        },
        {
            "id": str(CONTEXT_EVENT_IDS[15]),
            "user_id": str(USER_ID),
            "source": "calendar",
            "source_id": "cal-002",
            "event_type": "meeting",
            "content": "Investor call with David Kim from KV Capital. Third conversation. Discussed product vision, market opportunity, and fundraising details. David interested in leading $500-750K. Wants demo in 2 weeks and a pilot reference.",
            "structured_data": json.dumps({"calendar": "primary", "attendees": ["david@kv-capital.com"], "duration_minutes": 45}),
            "timestamp": ts(-12),
            "extracted_entities": json.dumps([{"type": "person", "value": "David Kim"}, {"type": "organization", "value": "KV Capital"}]),
            "extracted_people": ["David Kim"],
            "topics": ["fundraising", "investor relations", "seed round", "KV Capital"],
            "action_items": json.dumps([{"task": "Send updated pitch deck"}, {"task": "Schedule demo"}, {"task": "Connect David with James Liu"}]),
            "tier0_at": ts(-12),
            "tier1_at": ts(-11),
            "tier2_at": ts(-6),
            "created_at": ts(-12),
        },
        {
            "id": str(CONTEXT_EVENT_IDS[16]),
            "user_id": str(USER_ID),
            "source": "calendar",
            "source_id": "cal-003",
            "event_type": "meeting",
            "content": "Design review with Marcus Rivera and Sarah Chen. Reviewed token-based design system, dashboard redesign with workspace metaphor, and mobile responsive strategy. Agreed on web-first approach.",
            "structured_data": json.dumps({"calendar": "primary", "attendees": ["marcus@nexus.io", "sarah@nexus.io"], "duration_minutes": 60}),
            "timestamp": ts(-5),
            "extracted_entities": json.dumps([{"type": "person", "value": "Marcus Rivera"}, {"type": "person", "value": "Sarah Chen"}]),
            "extracted_people": ["Marcus Rivera", "Sarah Chen"],
            "topics": ["design", "design system", "dashboard", "mobile strategy"],
            "action_items": json.dumps([{"task": "Marcus to finalize dashboard specs"}, {"task": "Sarah to prototype drag-and-drop"}]),
            "tier0_at": ts(-5),
            "tier1_at": ts(-4),
            "tier2_at": None,
            "created_at": ts(-5),
        },
        {
            "id": str(CONTEXT_EVENT_IDS[17]),
            "user_id": str(USER_ID),
            "source": "calendar",
            "source_id": "cal-004",
            "event_type": "meeting",
            "content": "Marketing strategy call with Emma Thompson. Discussed PLG model, content marketing approach, landing page optimization. Emma recommends free tier and front-loading problem-awareness content.",
            "structured_data": json.dumps({"calendar": "primary", "attendees": ["emma@growthlab.co"], "duration_minutes": 45}),
            "timestamp": ts(-8),
            "extracted_entities": json.dumps([{"type": "person", "value": "Emma Thompson"}, {"type": "organization", "value": "GrowthLab"}]),
            "extracted_people": ["Emma Thompson"],
            "topics": ["marketing", "PLG", "growth strategy", "content marketing"],
            "action_items": json.dumps([{"task": "Design free tier limits"}, {"task": "Connect with Anika for content"}]),
            "tier0_at": ts(-8),
            "tier1_at": ts(-7),
            "tier2_at": None,
            "created_at": ts(-8),
        },
        # Manual note events
        {
            "id": str(CONTEXT_EVENT_IDS[18]),
            "user_id": str(USER_ID),
            "source": "manual_note",
            "source_id": "note-001",
            "event_type": "note",
            "content": "Realized we need to thread the needle between investor demo features and enterprise pilot features. Strategy: prioritize features that serve both audiences. Real-time collab impresses investors AND helps Acme. SSO signals maturity to investors AND is required by James.",
            "structured_data": json.dumps({"note_type": "insight"}),
            "timestamp": ts(-6),
            "extracted_entities": json.dumps([{"type": "person", "value": "David Kim"}, {"type": "person", "value": "James Liu"}, {"type": "organization", "value": "Acme Corp"}]),
            "extracted_people": ["David Kim", "James Liu"],
            "topics": ["strategy", "prioritization", "product roadmap"],
            "action_items": None,
            "tier0_at": ts(-6),
            "tier1_at": ts(-5),
            "tier2_at": None,
            "created_at": ts(-6),
        },
        {
            "id": str(CONTEXT_EVENT_IDS[19]),
            "user_id": str(USER_ID),
            "source": "manual_note",
            "source_id": "note-002",
            "event_type": "note",
            "content": "Competitive insight: none of the major players (Notion, Coda, Linear) do cross-content-type real-time collaboration. That's our wedge. Need to make this central to the pitch deck and marketing messaging.",
            "structured_data": json.dumps({"note_type": "insight"}),
            "timestamp": ts(-20),
            "extracted_entities": json.dumps([{"type": "organization", "value": "Notion"}, {"type": "organization", "value": "Linear"}]),
            "extracted_people": [],
            "topics": ["competitive analysis", "positioning", "differentiation"],
            "action_items": None,
            "tier0_at": ts(-20),
            "tier1_at": ts(-19),
            "tier2_at": ts(-10),
            "created_at": ts(-20),
        },
        {
            "id": str(CONTEXT_EVENT_IDS[20]),
            "user_id": str(USER_ID),
            "source": "manual_note",
            "source_id": "note-003",
            "event_type": "note",
            "content": "Had a great conversation with Emma about brand positioning. She emphasized: 'clear over clever'. Our messaging should be direct and avoid the buzzword salad that plagues the collaboration tools space. Anika's writing style aligns perfectly with this.",
            "structured_data": json.dumps({"note_type": "reflection"}),
            "timestamp": ts(-9),
            "extracted_entities": json.dumps([{"type": "person", "value": "Emma Thompson"}, {"type": "person", "value": "Anika Sharma"}]),
            "extracted_people": ["Emma Thompson", "Anika Sharma"],
            "topics": ["brand", "messaging", "marketing"],
            "action_items": None,
            "tier0_at": ts(-9),
            "tier1_at": ts(-8),
            "tier2_at": None,
            "created_at": ts(-9),
        },
        # Older events for activity heatmap spread
        {
            "id": str(CONTEXT_EVENT_IDS[21]),
            "user_id": str(USER_ID),
            "source": "email",
            "source_id": "email-005",
            "event_type": "email_received",
            "content": "Lisa Park from Gradient Ventures expressed interest in our seed round. She saw our HN post and liked the technical depth. Wants to schedule a pitch meeting.",
            "structured_data": json.dumps({"from": "lisa@gradient.vc", "subject": "Nexus - Gradient Ventures interest"}),
            "timestamp": ts(-25),
            "extracted_entities": json.dumps([{"type": "person", "value": "Lisa Park"}, {"type": "organization", "value": "Gradient Ventures"}]),
            "extracted_people": ["Lisa Park"],
            "topics": ["fundraising", "investor outreach", "seed round"],
            "action_items": json.dumps([{"task": "Schedule pitch with Lisa Park", "priority": "high"}]),
            "tier0_at": ts(-25),
            "tier1_at": ts(-24),
            "tier2_at": ts(-15),
            "created_at": ts(-25),
        },
        {
            "id": str(CONTEXT_EVENT_IDS[22]),
            "user_id": str(USER_ID),
            "source": "github",
            "source_id": "pr-020",
            "event_type": "pr_merged",
            "content": "PR #20 merged: 'feat: initial project setup with FastAPI, PostgreSQL, and React'. Monorepo structure, CI/CD with GitHub Actions, Docker compose for local development.",
            "structured_data": json.dumps({"repo": "nexus-app/nexus", "pr_number": 20, "author": "priya-patel", "additions": 4500, "deletions": 0}),
            "timestamp": ts(-45),
            "extracted_entities": json.dumps([{"type": "person", "value": "Priya Patel"}, {"type": "technology", "value": "FastAPI"}, {"type": "technology", "value": "React"}]),
            "extracted_people": ["Priya Patel"],
            "topics": ["project setup", "infrastructure", "DevOps"],
            "action_items": None,
            "tier0_at": ts(-45),
            "tier1_at": ts(-44),
            "tier2_at": ts(-30),
            "created_at": ts(-45),
        },
        {
            "id": str(CONTEXT_EVENT_IDS[23]),
            "user_id": str(USER_ID),
            "source": "slack",
            "source_id": "slack-010",
            "event_type": "message",
            "content": "Emma Thompson in #marketing: 'Just reviewed the HN analytics — 200+ signups from a single post is solid traction for pre-product. Let's capture this momentum with a drip email sequence. I'll draft the 5-email onboarding flow.'",
            "structured_data": json.dumps({"channel": "#marketing", "thread_ts": "1710500000.000600"}),
            "timestamp": ts(-18),
            "extracted_entities": json.dumps([{"type": "person", "value": "Emma Thompson"}]),
            "extracted_people": ["Emma Thompson"],
            "topics": ["marketing", "growth", "email marketing", "waitlist"],
            "action_items": json.dumps([{"task": "Emma to draft email onboarding sequence", "priority": "medium"}]),
            "tier0_at": ts(-18),
            "tier1_at": ts(-17),
            "tier2_at": ts(-10),
            "created_at": ts(-18),
        },
        {
            "id": str(CONTEXT_EVENT_IDS[24]),
            "user_id": str(USER_ID),
            "source": "calendar",
            "source_id": "cal-010",
            "event_type": "meeting",
            "content": "Initial call with James Liu from Acme Corp. He learned about Nexus through a former colleague. His 200-person engineering team uses Confluence + Slack + Linear and the context switching is killing productivity. Very interested in a pilot.",
            "structured_data": json.dumps({"calendar": "primary", "attendees": ["james@acmecorp.com"], "duration_minutes": 30}),
            "timestamp": ts(-30),
            "extracted_entities": json.dumps([{"type": "person", "value": "James Liu"}, {"type": "organization", "value": "Acme Corp"}]),
            "extracted_people": ["James Liu"],
            "topics": ["enterprise", "pilot", "Acme Corp", "sales"],
            "action_items": json.dumps([{"task": "Send pilot proposal to James", "priority": "high"}]),
            "tier0_at": ts(-30),
            "tier1_at": ts(-29),
            "tier2_at": ts(-15),
            "created_at": ts(-30),
        },
        {
            "id": str(CONTEXT_EVENT_IDS[25]),
            "user_id": str(USER_ID),
            "source": "slack",
            "source_id": "slack-011",
            "event_type": "message",
            "content": "Marcus Rivera in #design: 'Brand exploration update — I've landed on the Connected Nodes concept for the logo. Geometric mark of three interconnected nodes forming the letter N. Going with the minimal variant. Also evolved the color palette: amber primary, coral secondary, charcoal dark.'",
            "structured_data": json.dumps({"channel": "#design", "thread_ts": "1711200000.000700"}),
            "timestamp": ts(-10),
            "extracted_entities": json.dumps([{"type": "person", "value": "Marcus Rivera"}]),
            "extracted_people": ["Marcus Rivera"],
            "topics": ["brand identity", "logo design", "visual design"],
            "action_items": None,
            "tier0_at": ts(-10),
            "tier1_at": ts(-9),
            "tier2_at": None,
            "created_at": ts(-10),
        },
        {
            "id": str(CONTEXT_EVENT_IDS[26]),
            "user_id": str(USER_ID),
            "source": "email",
            "source_id": "email-006",
            "event_type": "email_received",
            "content": "David Kim forwarded an article: 'The Collaboration Software Market in 2025: Winners and Losers'. Added a note: 'This aligns with what you showed me about the fragmentation problem. Worth referencing in the deck.'",
            "structured_data": json.dumps({"from": "david@kv-capital.com", "subject": "FW: Collaboration market trends article"}),
            "timestamp": ts(-35),
            "extracted_entities": json.dumps([{"type": "person", "value": "David Kim"}, {"type": "organization", "value": "KV Capital"}]),
            "extracted_people": ["David Kim"],
            "topics": ["market research", "fundraising", "investor engagement"],
            "action_items": None,
            "tier0_at": ts(-35),
            "tier1_at": ts(-34),
            "tier2_at": ts(-20),
            "created_at": ts(-35),
        },
        {
            "id": str(CONTEXT_EVENT_IDS[27]),
            "user_id": str(USER_ID),
            "source": "github",
            "source_id": "pr-025",
            "event_type": "pr_merged",
            "content": "PR #25 merged: 'feat: design system foundation with Tailwind tokens'. Token-based design system, color palette, typography scale, spacing system, and core components (Button, Input, Card, Modal).",
            "structured_data": json.dumps({"repo": "nexus-app/nexus", "pr_number": 25, "author": "sarah-chen", "additions": 2800, "deletions": 450}),
            "timestamp": ts(-30),
            "extracted_entities": json.dumps([{"type": "person", "value": "Sarah Chen"}, {"type": "person", "value": "Marcus Rivera"}, {"type": "technology", "value": "Tailwind"}]),
            "extracted_people": ["Sarah Chen", "Marcus Rivera"],
            "topics": ["design system", "frontend", "UI components"],
            "action_items": None,
            "tier0_at": ts(-30),
            "tier1_at": ts(-29),
            "tier2_at": ts(-15),
            "created_at": ts(-30),
        },
        {
            "id": str(CONTEXT_EVENT_IDS[28]),
            "user_id": str(USER_ID),
            "source": "manual_note",
            "source_id": "note-004",
            "event_type": "note",
            "content": "Team retrospective thoughts: we're moving fast but need better async communication. Too many impromptu Slack threads that lose context. Ironic that we're building a tool to solve this. Should dogfood Nexus as soon as the MVP is usable.",
            "structured_data": json.dumps({"note_type": "reflection"}),
            "timestamp": ts(-15),
            "extracted_entities": json.dumps([]),
            "extracted_people": [],
            "topics": ["team culture", "process improvement", "dogfooding"],
            "action_items": None,
            "tier0_at": ts(-15),
            "tier1_at": ts(-14),
            "tier2_at": ts(-7),
            "created_at": ts(-15),
        },
        {
            "id": str(CONTEXT_EVENT_IDS[29]),
            "user_id": str(USER_ID),
            "source": "email",
            "source_id": "email-007",
            "event_type": "email_received",
            "content": "Anika Sharma confirmed availability for the content writing engagement. Rate: $150/hour, estimated 20 hours for initial batch (4 blog posts + landing page copy). Starting with the 'Why Your Team Tools Don't Talk' piece.",
            "structured_data": json.dumps({"from": "anika@freelance.dev", "subject": "Re: Content writing engagement - Nexus"}),
            "timestamp": ts(-20),
            "extracted_entities": json.dumps([{"type": "person", "value": "Anika Sharma"}]),
            "extracted_people": ["Anika Sharma"],
            "topics": ["content", "freelance", "marketing launch"],
            "action_items": json.dumps([{"task": "Send Anika brand guidelines and content brief", "priority": "medium"}]),
            "tier0_at": ts(-20),
            "tier1_at": ts(-19),
            "tier2_at": ts(-10),
            "created_at": ts(-20),
        },
    ]
    for e in events:
        await conn.execute(text("""
            INSERT INTO context_events (id, user_id, source, source_id, event_type, content,
                                        structured_data, timestamp, extracted_entities,
                                        extracted_people, topics, action_items,
                                        tier0_at, tier1_at, tier2_at, created_at)
            VALUES (:id, :user_id, :source, :source_id, :event_type, :content,
                    :structured_data::jsonb, :timestamp, :extracted_entities::jsonb,
                    :extracted_people, :topics, :action_items::jsonb,
                    :tier0_at, :tier1_at, :tier2_at, :created_at)
            ON CONFLICT DO NOTHING
        """), e)


async def insert_thoughts(conn):
    print("  Inserting thoughts...")
    thoughts = [
        {
            "id": str(THOUGHT_IDS[0]),
            "user_id": str(USER_ID),
            "content": "The key to winning the seed round is demonstrating that Nexus can do what no other collaboration tool does: real-time collaboration across different content types. Sarah's CRDT engine is our technical moat and David Kim recognized it immediately.",
            "timestamp": ts(-3),
            "thought_metadata": json.dumps({"source": "reflection", "mood": "optimistic", "context": "fundraising"}),
            "created_at": ts(-3),
            "updated_at": ts(-3),
        },
        {
            "id": str(THOUGHT_IDS[1]),
            "user_id": str(USER_ID),
            "content": "Priya's velocity on the auth system is impressive. She went from zero to full OAuth2 + magic links in under two weeks. If she maintains this pace on the API layer, we'll have a demo-ready product ahead of schedule for David Kim's timeline.",
            "timestamp": ts(-1),
            "thought_metadata": json.dumps({"source": "observation", "mood": "impressed", "context": "team performance"}),
            "created_at": ts(-1),
            "updated_at": ts(-1),
        },
        {
            "id": str(THOUGHT_IDS[2]),
            "user_id": str(USER_ID),
            "content": "The tension between enterprise features for Acme Corp and demo features for investors is real. James Liu needs SSO and admin panels. David Kim wants to see polished real-time collaboration. The solution is to find features that serve both — SSO signals maturity to investors too.",
            "timestamp": ts(-6),
            "thought_metadata": json.dumps({"source": "analysis", "mood": "strategic", "context": "prioritization"}),
            "created_at": ts(-6),
            "updated_at": ts(-6),
        },
        {
            "id": str(THOUGHT_IDS[3]),
            "user_id": str(USER_ID),
            "content": "Emma's PLG insight is valuable: the best developer tools let you experience the product before buying. A limited free tier (3 users, 1 workspace) costs us almost nothing in infrastructure but could dramatically improve conversion from our 200+ waitlist.",
            "timestamp": ts(-8),
            "thought_metadata": json.dumps({"source": "conversation", "mood": "excited", "context": "go-to-market"}),
            "created_at": ts(-8),
            "updated_at": ts(-8),
        },
        {
            "id": str(THOUGHT_IDS[4]),
            "user_id": str(USER_ID),
            "content": "Marcus's brand evolution from corporate blue to amber/coral is exactly right. It differentiates us visually from every other collaboration tool (Slack, Notion, Linear — all blue/purple). The Connected Nodes logo concept ties perfectly into the Nexus name.",
            "timestamp": ts(-10),
            "thought_metadata": json.dumps({"source": "observation", "mood": "excited", "context": "brand identity"}),
            "created_at": ts(-10),
            "updated_at": ts(-10),
        },
        {
            "id": str(THOUGHT_IDS[5]),
            "user_id": str(USER_ID),
            "content": "We're building four things simultaneously: MVP, fundraising, marketing launch, and enterprise pilot. That's aggressive for a team of four. Need to be ruthless about prioritization. The fundraising timeline is the binding constraint — everything else follows from it.",
            "timestamp": ts(-4),
            "thought_metadata": json.dumps({"source": "reflection", "mood": "focused", "context": "strategy"}),
            "created_at": ts(-4),
            "updated_at": ts(-4),
        },
    ]
    for t in thoughts:
        await conn.execute(text("""
            INSERT INTO thoughts (id, user_id, content, timestamp, thought_metadata, created_at, updated_at)
            VALUES (:id, :user_id, :content, :timestamp, :thought_metadata::jsonb, :created_at, :updated_at)
            ON CONFLICT DO NOTHING
        """), t)


async def insert_semantic_entries(conn):
    print("  Inserting semantic entries...")
    entries = [
        {"id": str(SEMANTIC_IDS[0]),  "thought_id": str(THOUGHT_IDS[0]), "entity_type": "person",       "entity_value": "Sarah Chen",      "confidence": 0.95, "context": "Co-founder/CTO building the CRDT real-time engine",    "extracted_at": ts(-3)},
        {"id": str(SEMANTIC_IDS[1]),  "thought_id": str(THOUGHT_IDS[0]), "entity_type": "person",       "entity_value": "David Kim",       "confidence": 0.92, "context": "Investor at KV Capital interested in technical moat",  "extracted_at": ts(-3)},
        {"id": str(SEMANTIC_IDS[2]),  "thought_id": str(THOUGHT_IDS[0]), "entity_type": "technology",   "entity_value": "CRDT",            "confidence": 0.98, "context": "Conflict-free replicated data types for real-time",    "extracted_at": ts(-3)},
        {"id": str(SEMANTIC_IDS[3]),  "thought_id": str(THOUGHT_IDS[1]), "entity_type": "person",       "entity_value": "Priya Patel",     "confidence": 0.96, "context": "Backend engineer with fast velocity on auth system",   "extracted_at": ts(-1)},
        {"id": str(SEMANTIC_IDS[4]),  "thought_id": str(THOUGHT_IDS[1]), "entity_type": "technology",   "entity_value": "OAuth2",          "confidence": 0.90, "context": "Authentication protocol implemented by Priya",         "extracted_at": ts(-1)},
        {"id": str(SEMANTIC_IDS[5]),  "thought_id": str(THOUGHT_IDS[2]), "entity_type": "organization", "entity_value": "Acme Corp",       "confidence": 0.94, "context": "Enterprise pilot customer with 200-person eng team",   "extracted_at": ts(-6)},
        {"id": str(SEMANTIC_IDS[6]),  "thought_id": str(THOUGHT_IDS[2]), "entity_type": "person",       "entity_value": "James Liu",       "confidence": 0.91, "context": "VP Engineering at Acme Corp, pilot contact",           "extracted_at": ts(-6)},
        {"id": str(SEMANTIC_IDS[7]),  "thought_id": str(THOUGHT_IDS[2]), "entity_type": "project",      "entity_value": "Enterprise Pilot","confidence": 0.93, "context": "50-user trial deployment at Acme Corp",                "extracted_at": ts(-6)},
        {"id": str(SEMANTIC_IDS[8]),  "thought_id": str(THOUGHT_IDS[3]), "entity_type": "person",       "entity_value": "Emma Thompson",   "confidence": 0.94, "context": "Marketing advisor pushing PLG strategy",               "extracted_at": ts(-8)},
        {"id": str(SEMANTIC_IDS[9]),  "thought_id": str(THOUGHT_IDS[3]), "entity_type": "topic",        "entity_value": "Product-Led Growth", "confidence": 0.97, "context": "GTM strategy: let users experience before buying", "extracted_at": ts(-8)},
        {"id": str(SEMANTIC_IDS[10]), "thought_id": str(THOUGHT_IDS[4]), "entity_type": "person",       "entity_value": "Marcus Rivera",   "confidence": 0.95, "context": "Lead designer driving brand identity evolution",       "extracted_at": ts(-10)},
        {"id": str(SEMANTIC_IDS[11]), "thought_id": str(THOUGHT_IDS[4]), "entity_type": "topic",        "entity_value": "Brand Identity",  "confidence": 0.93, "context": "Visual direction: amber/coral palette, Connected Nodes","extracted_at": ts(-10)},
        {"id": str(SEMANTIC_IDS[12]), "thought_id": str(THOUGHT_IDS[5]), "entity_type": "project",      "entity_value": "Nexus MVP",       "confidence": 0.96, "context": "Core product build: auth, dashboard, API, collab",    "extracted_at": ts(-4)},
        {"id": str(SEMANTIC_IDS[13]), "thought_id": str(THOUGHT_IDS[5]), "entity_type": "project",      "entity_value": "Seed Fundraising","confidence": 0.94, "context": "$1.5M seed round, binding constraint on timeline",     "extracted_at": ts(-4)},
        {"id": str(SEMANTIC_IDS[14]), "thought_id": str(THOUGHT_IDS[0]), "entity_type": "organization", "entity_value": "KV Capital",      "confidence": 0.91, "context": "VC fund, potential lead investor for seed round",      "extracted_at": ts(-3)},
        {"id": str(SEMANTIC_IDS[15]), "thought_id": str(THOUGHT_IDS[3]), "entity_type": "organization", "entity_value": "GrowthLab",       "confidence": 0.85, "context": "Emma Thompson's consulting firm for marketing",        "extracted_at": ts(-8)},
    ]
    for e in entries:
        await conn.execute(text("""
            INSERT INTO semantic_entries (id, thought_id, entity_type, entity_value, confidence, context, extracted_at)
            VALUES (:id, :thought_id, :entity_type, :entity_value, :confidence, :context, :extracted_at)
            ON CONFLICT DO NOTHING
        """), e)


async def insert_entity_relationships(conn):
    print("  Inserting entity relationships...")
    rels = [
        {"id": str(RELATIONSHIP_IDS[0]),  "source_entity_id": str(SEMANTIC_IDS[0]),  "target_entity_id": str(SEMANTIC_IDS[2]),  "relationship_type": "builds",           "strength": 0.95, "created_at": ts(-3)},
        {"id": str(RELATIONSHIP_IDS[1]),  "source_entity_id": str(SEMANTIC_IDS[1]),  "target_entity_id": str(SEMANTIC_IDS[14]), "relationship_type": "works_at",         "strength": 0.98, "created_at": ts(-3)},
        {"id": str(RELATIONSHIP_IDS[2]),  "source_entity_id": str(SEMANTIC_IDS[3]),  "target_entity_id": str(SEMANTIC_IDS[4]),  "relationship_type": "implements",       "strength": 0.92, "created_at": ts(-1)},
        {"id": str(RELATIONSHIP_IDS[3]),  "source_entity_id": str(SEMANTIC_IDS[6]),  "target_entity_id": str(SEMANTIC_IDS[5]),  "relationship_type": "works_at",         "strength": 0.97, "created_at": ts(-6)},
        {"id": str(RELATIONSHIP_IDS[4]),  "source_entity_id": str(SEMANTIC_IDS[6]),  "target_entity_id": str(SEMANTIC_IDS[7]),  "relationship_type": "stakeholder_of",   "strength": 0.90, "created_at": ts(-6)},
        {"id": str(RELATIONSHIP_IDS[5]),  "source_entity_id": str(SEMANTIC_IDS[8]),  "target_entity_id": str(SEMANTIC_IDS[9]),  "relationship_type": "advocates",        "strength": 0.93, "created_at": ts(-8)},
        {"id": str(RELATIONSHIP_IDS[6]),  "source_entity_id": str(SEMANTIC_IDS[8]),  "target_entity_id": str(SEMANTIC_IDS[15]), "relationship_type": "works_at",         "strength": 0.96, "created_at": ts(-8)},
        {"id": str(RELATIONSHIP_IDS[7]),  "source_entity_id": str(SEMANTIC_IDS[10]), "target_entity_id": str(SEMANTIC_IDS[11]), "relationship_type": "designs",          "strength": 0.94, "created_at": ts(-10)},
        {"id": str(RELATIONSHIP_IDS[8]),  "source_entity_id": str(SEMANTIC_IDS[12]), "target_entity_id": str(SEMANTIC_IDS[13]), "relationship_type": "depends_on",       "strength": 0.88, "created_at": ts(-4)},
        {"id": str(RELATIONSHIP_IDS[9]),  "source_entity_id": str(SEMANTIC_IDS[1]),  "target_entity_id": str(SEMANTIC_IDS[13]), "relationship_type": "evaluates",        "strength": 0.85, "created_at": ts(-3)},
        {"id": str(RELATIONSHIP_IDS[10]), "source_entity_id": str(SEMANTIC_IDS[0]),  "target_entity_id": str(SEMANTIC_IDS[12]), "relationship_type": "contributes_to",   "strength": 0.96, "created_at": ts(-3)},
    ]
    for r in rels:
        await conn.execute(text("""
            INSERT INTO entity_relationships (id, source_entity_id, target_entity_id, relationship_type, strength, created_at)
            VALUES (:id, :source_entity_id, :target_entity_id, :relationship_type, :strength, :created_at)
            ON CONFLICT DO NOTHING
        """), r)


async def insert_note_associations(conn):
    print("  Inserting note associations...")
    assocs = [
        # Meeting notes → people
        {"id": str(NOTE_ASSOC_IDS[0]),  "user_id": str(USER_ID), "note_id": str(NOTE_IDS["team-standup-apr-7"]),   "object_type": "person",  "object_id": str(PEOPLE_IDS["sarah"]),  "relationship": "attendee",    "confidence": 0.98, "created_at": ts(-1)},
        {"id": str(NOTE_ASSOC_IDS[1]),  "user_id": str(USER_ID), "note_id": str(NOTE_IDS["team-standup-apr-7"]),   "object_type": "person",  "object_id": str(PEOPLE_IDS["priya"]),  "relationship": "attendee",    "confidence": 0.98, "created_at": ts(-1)},
        {"id": str(NOTE_ASSOC_IDS[2]),  "user_id": str(USER_ID), "note_id": str(NOTE_IDS["team-standup-apr-7"]),   "object_type": "person",  "object_id": str(PEOPLE_IDS["marcus"]), "relationship": "attendee",    "confidence": 0.98, "created_at": ts(-1)},
        {"id": str(NOTE_ASSOC_IDS[3]),  "user_id": str(USER_ID), "note_id": str(NOTE_IDS["investor-call-david"]),  "object_type": "person",  "object_id": str(PEOPLE_IDS["david"]),  "relationship": "attendee",    "confidence": 0.97, "created_at": ts(-12)},
        {"id": str(NOTE_ASSOC_IDS[4]),  "user_id": str(USER_ID), "note_id": str(NOTE_IDS["design-review-q2"]),     "object_type": "person",  "object_id": str(PEOPLE_IDS["marcus"]), "relationship": "attendee",    "confidence": 0.98, "created_at": ts(-5)},
        {"id": str(NOTE_ASSOC_IDS[5]),  "user_id": str(USER_ID), "note_id": str(NOTE_IDS["design-review-q2"]),     "object_type": "person",  "object_id": str(PEOPLE_IDS["sarah"]),  "relationship": "attendee",    "confidence": 0.98, "created_at": ts(-5)},
        # Project notes → projects
        {"id": str(NOTE_ASSOC_IDS[6]),  "user_id": str(USER_ID), "note_id": str(NOTE_IDS["nexus-mvp-spec"]),       "object_type": "project", "object_id": str(PROJECT_IDS["nexus_mvp"]),       "relationship": "specification", "confidence": 0.99, "created_at": ts(-45)},
        {"id": str(NOTE_ASSOC_IDS[7]),  "user_id": str(USER_ID), "note_id": str(NOTE_IDS["fundraising-tracker"]),  "object_type": "project", "object_id": str(PROJECT_IDS["seed_fundraising"]), "relationship": "tracker",       "confidence": 0.99, "created_at": ts(-30)},
        {"id": str(NOTE_ASSOC_IDS[8]),  "user_id": str(USER_ID), "note_id": str(NOTE_IDS["marketing-plan"]),       "object_type": "project", "object_id": str(PROJECT_IDS["marketing_launch"]), "relationship": "plan",          "confidence": 0.99, "created_at": ts(-20)},
        {"id": str(NOTE_ASSOC_IDS[9]),  "user_id": str(USER_ID), "note_id": str(NOTE_IDS["enterprise-pilot-notes"]), "object_type": "project", "object_id": str(PROJECT_IDS["enterprise_pilot"]), "relationship": "plan",       "confidence": 0.99, "created_at": ts(-15)},
        # Cross-references: notes mentioning people
        {"id": str(NOTE_ASSOC_IDS[10]), "user_id": str(USER_ID), "note_id": str(NOTE_IDS["marketing-plan"]),       "object_type": "person",  "object_id": str(PEOPLE_IDS["emma"]),   "relationship": "mentioned",   "confidence": 0.90, "created_at": ts(-20)},
        {"id": str(NOTE_ASSOC_IDS[11]), "user_id": str(USER_ID), "note_id": str(NOTE_IDS["marketing-plan"]),       "object_type": "person",  "object_id": str(PEOPLE_IDS["anika"]),  "relationship": "mentioned",   "confidence": 0.88, "created_at": ts(-20)},
        {"id": str(NOTE_ASSOC_IDS[12]), "user_id": str(USER_ID), "note_id": str(NOTE_IDS["enterprise-pilot-notes"]), "object_type": "person",  "object_id": str(PEOPLE_IDS["james"]),  "relationship": "primary_contact", "confidence": 0.97, "created_at": ts(-15)},
        {"id": str(NOTE_ASSOC_IDS[13]), "user_id": str(USER_ID), "note_id": str(NOTE_IDS["brand-identity"]),       "object_type": "person",  "object_id": str(PEOPLE_IDS["marcus"]), "relationship": "owner",       "confidence": 0.95, "created_at": ts(-10)},
        {"id": str(NOTE_ASSOC_IDS[14]), "user_id": str(USER_ID), "note_id": str(NOTE_IDS["competitor-analysis"]),  "object_type": "project", "object_id": str(PROJECT_IDS["marketing_launch"]), "relationship": "reference", "confidence": 0.85, "created_at": ts(-25)},
        {"id": str(NOTE_ASSOC_IDS[15]), "user_id": str(USER_ID), "note_id": str(NOTE_IDS["feature-prioritization"]), "object_type": "project", "object_id": str(PROJECT_IDS["nexus_mvp"]),     "relationship": "planning",  "confidence": 0.92, "created_at": ts(-7)},
    ]
    for a in assocs:
        await conn.execute(text("""
            INSERT INTO note_associations (id, user_id, note_id, object_type, object_id, relationship, confidence, created_at)
            VALUES (:id, :user_id, :note_id, :object_type, :object_id, :relationship, :confidence, :created_at)
            ON CONFLICT DO NOTHING
        """), a)


async def insert_note_metadata(conn):
    print("  Inserting note metadata...")
    meta = [
        {"note_id": str(NOTE_IDS["team-standup-apr-7"]),     "user_id": str(USER_ID), "lifecycle": "active",    "last_meaningful_edit": ts(-1),  "view_count": 5,  "importance_score": 0.85, "distilled_at": None,    "source_type": "meeting"},
        {"note_id": str(NOTE_IDS["investor-call-david"]),    "user_id": str(USER_ID), "lifecycle": "active",    "last_meaningful_edit": ts(-10), "view_count": 12, "importance_score": 0.95, "distilled_at": None,    "source_type": "meeting"},
        {"note_id": str(NOTE_IDS["design-review-q2"]),       "user_id": str(USER_ID), "lifecycle": "active",    "last_meaningful_edit": ts(-5),  "view_count": 4,  "importance_score": 0.70, "distilled_at": None,    "source_type": "meeting"},
        {"note_id": str(NOTE_IDS["nexus-mvp-spec"]),         "user_id": str(USER_ID), "lifecycle": "active",    "last_meaningful_edit": ts(-2),  "view_count": 25, "importance_score": 0.98, "distilled_at": None,    "source_type": "document"},
        {"note_id": str(NOTE_IDS["fundraising-tracker"]),    "user_id": str(USER_ID), "lifecycle": "active",    "last_meaningful_edit": ts(-3),  "view_count": 18, "importance_score": 0.95, "distilled_at": None,    "source_type": "document"},
        {"note_id": str(NOTE_IDS["marketing-plan"]),         "user_id": str(USER_ID), "lifecycle": "active",    "last_meaningful_edit": ts(-2),  "view_count": 10, "importance_score": 0.80, "distilled_at": None,    "source_type": "document"},
        {"note_id": str(NOTE_IDS["enterprise-pilot-notes"]), "user_id": str(USER_ID), "lifecycle": "active",    "last_meaningful_edit": ts(-8),  "view_count": 8,  "importance_score": 0.85, "distilled_at": None,    "source_type": "document"},
        {"note_id": str(NOTE_IDS["daily-apr-7"]),            "user_id": str(USER_ID), "lifecycle": "active",    "last_meaningful_edit": ts(0, -1), "view_count": 2, "importance_score": 0.50, "distilled_at": None,   "source_type": "journal"},
        {"note_id": str(NOTE_IDS["daily-apr-6"]),            "user_id": str(USER_ID), "lifecycle": "active",    "last_meaningful_edit": ts(-1, -1), "view_count": 3, "importance_score": 0.45, "distilled_at": None,  "source_type": "journal"},
        {"note_id": str(NOTE_IDS["weekly-reflection-w14"]),  "user_id": str(USER_ID), "lifecycle": "active",    "last_meaningful_edit": ts(-3),  "view_count": 6,  "importance_score": 0.75, "distilled_at": None,    "source_type": "journal"},
        {"note_id": str(NOTE_IDS["payment-provider"]),       "user_id": str(USER_ID), "lifecycle": "settled",   "last_meaningful_edit": ts(-14), "view_count": 7,  "importance_score": 0.70, "distilled_at": ts(-10), "source_type": "decision"},
        {"note_id": str(NOTE_IDS["target-market"]),          "user_id": str(USER_ID), "lifecycle": "settled",   "last_meaningful_edit": ts(-21), "view_count": 9,  "importance_score": 0.80, "distilled_at": ts(-14), "source_type": "decision"},
        {"note_id": str(NOTE_IDS["feature-prioritization"]), "user_id": str(USER_ID), "lifecycle": "active",    "last_meaningful_edit": ts(-1),  "view_count": 14, "importance_score": 0.88, "distilled_at": None,    "source_type": "document"},
        {"note_id": str(NOTE_IDS["brand-identity"]),         "user_id": str(USER_ID), "lifecycle": "active",    "last_meaningful_edit": ts(-5),  "view_count": 6,  "importance_score": 0.65, "distilled_at": None,    "source_type": "document"},
        {"note_id": str(NOTE_IDS["competitor-analysis"]),    "user_id": str(USER_ID), "lifecycle": "active",    "last_meaningful_edit": ts(-5),  "view_count": 11, "importance_score": 0.82, "distilled_at": None,    "source_type": "reference"},
    ]
    for m in meta:
        await conn.execute(text("""
            INSERT INTO note_metadata (note_id, user_id, lifecycle, last_meaningful_edit, view_count,
                                       importance_score, distilled_at, source_type)
            VALUES (:note_id, :user_id, :lifecycle, :last_meaningful_edit, :view_count,
                    :importance_score, :distilled_at, :source_type)
            ON CONFLICT DO NOTHING
        """), m)


async def insert_commitments(conn):
    print("  Inserting commitments...")
    commitments = [
        {
            "id": str(COMMITMENT_IDS[0]),
            "user_id": str(USER_ID),
            "event_id": str(CONTEXT_EVENT_IDS[15]),
            "person_id": str(PEOPLE_IDS["david"]),
            "description": "Send David Kim the updated pitch deck with revised TAM analysis and financial projections",
            "due_date": ts(3),
            "status": "open",
            "fulfilled_event_id": None,
            "created_at": ts(-12),
            "updated_at": ts(-2),
        },
        {
            "id": str(COMMITMENT_IDS[1]),
            "user_id": str(USER_ID),
            "event_id": str(CONTEXT_EVENT_IDS[1]),
            "person_id": str(PEOPLE_IDS["james"]),
            "description": "Schedule a product demo for James Liu and the Acme Corp engineering team",
            "due_date": ts(-2),
            "status": "open",
            "fulfilled_event_id": None,
            "created_at": ts(-15),
            "updated_at": ts(-5),
        },
        {
            "id": str(COMMITMENT_IDS[2]),
            "user_id": str(USER_ID),
            "event_id": str(CONTEXT_EVENT_IDS[17]),
            "person_id": str(PEOPLE_IDS["emma"]),
            "description": "Incorporate Emma Thompson's feedback on pitch deck v3 and share revised version",
            "due_date": ts(5),
            "status": "open",
            "fulfilled_event_id": None,
            "created_at": ts(-8),
            "updated_at": ts(-4),
        },
        {
            "id": str(COMMITMENT_IDS[3]),
            "user_id": str(USER_ID),
            "event_id": str(CONTEXT_EVENT_IDS[14]),
            "person_id": str(PEOPLE_IDS["priya"]),
            "description": "Review Priya's authentication PR with focus on token rotation logic",
            "due_date": ts(0),
            "status": "open",
            "fulfilled_event_id": None,
            "created_at": ts(-1),
            "updated_at": ts(-1),
        },
    ]
    for c in commitments:
        await conn.execute(text("""
            INSERT INTO commitments (id, user_id, event_id, person_id, description, due_date,
                                     status, fulfilled_event_id, created_at, updated_at)
            VALUES (:id, :user_id, :event_id, :person_id, :description, :due_date,
                    :status, :fulfilled_event_id, :created_at, :updated_at)
            ON CONFLICT DO NOTHING
        """), c)


async def insert_connections(conn):
    print("  Inserting connections...")
    conns = [
        {
            "id": str(CONNECTION_IDS[0]),
            "user_id": str(USER_ID),
            "source_event_id": str(CONTEXT_EVENT_IDS[0]),
            "target_event_id": str(CONTEXT_EVENT_IDS[15]),
            "connection_type": "follow_up",
            "strength": 0.92,
            "evidence": "David Kim's email follow-up references the investor call discussion about architecture",
            "discovered_at": ts(-2),
            "method": "entity_match",
            "last_confirmed_at": ts(-1),
        },
        {
            "id": str(CONNECTION_IDS[1]),
            "user_id": str(USER_ID),
            "source_event_id": str(CONTEXT_EVENT_IDS[5]),
            "target_event_id": str(CONTEXT_EVENT_IDS[9]),
            "connection_type": "related",
            "strength": 0.95,
            "evidence": "Priya's Slack message about auth PR references the same OAuth2 PR merged on GitHub",
            "discovered_at": ts(-1),
            "method": "entity_match",
            "last_confirmed_at": ts(-1),
        },
        {
            "id": str(CONNECTION_IDS[2]),
            "user_id": str(USER_ID),
            "source_event_id": str(CONTEXT_EVENT_IDS[2]),
            "target_event_id": str(CONTEXT_EVENT_IDS[17]),
            "connection_type": "follow_up",
            "strength": 0.88,
            "evidence": "Emma's pitch deck feedback email follows the marketing strategy meeting",
            "discovered_at": ts(-8),
            "method": "temporal_proximity",
            "last_confirmed_at": ts(-7),
        },
        {
            "id": str(CONNECTION_IDS[3]),
            "user_id": str(USER_ID),
            "source_event_id": str(CONTEXT_EVENT_IDS[1]),
            "target_event_id": str(CONTEXT_EVENT_IDS[24]),
            "connection_type": "follow_up",
            "strength": 0.90,
            "evidence": "James Liu's pilot confirmation email follows the initial discovery call",
            "discovered_at": ts(-15),
            "method": "entity_match",
            "last_confirmed_at": ts(-12),
        },
        {
            "id": str(CONNECTION_IDS[4]),
            "user_id": str(USER_ID),
            "source_event_id": str(CONTEXT_EVENT_IDS[4]),
            "target_event_id": str(CONTEXT_EVENT_IDS[10]),
            "connection_type": "related",
            "strength": 0.87,
            "evidence": "Sarah's stress test results inform the infrastructure foundation from the CRDT PR",
            "discovered_at": ts(-3),
            "method": "topic_similarity",
            "last_confirmed_at": ts(-2),
        },
        {
            "id": str(CONNECTION_IDS[5]),
            "user_id": str(USER_ID),
            "source_event_id": str(CONTEXT_EVENT_IDS[3]),
            "target_event_id": str(CONTEXT_EVENT_IDS[29]),
            "connection_type": "related",
            "strength": 0.85,
            "evidence": "Anika's blog draft delivery connects to the original content engagement email",
            "discovered_at": ts(-4),
            "method": "entity_match",
            "last_confirmed_at": ts(-3),
        },
    ]
    for c in conns:
        await conn.execute(text("""
            INSERT INTO connections (id, user_id, source_event_id, target_event_id, connection_type,
                                     strength, evidence, discovered_at, method, last_confirmed_at)
            VALUES (:id, :user_id, :source_event_id, :target_event_id, :connection_type,
                    :strength, :evidence, :discovered_at, :method, :last_confirmed_at)
            ON CONFLICT DO NOTHING
        """), c)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def seed():
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        print("ERROR: DATABASE_URL not set in .env")
        sys.exit(1)

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    parsed = urlparse(database_url)
    params = parse_qs(parsed.query)
    params.pop("sslmode", None)
    clean_query = urlencode(params, doseq=True)
    database_url = urlunparse(parsed._replace(query=clean_query))

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    engine = create_async_engine(database_url, connect_args={"ssl": ctx})

    print("Starting Einstein mock data seed...")
    print(f"  Database: {parsed.hostname}")
    print(f"  User ID:  {USER_ID}")
    print()

    async with engine.begin() as conn:
        await insert_user(conn)
        await insert_people(conn)
        await insert_projects(conn)
        await insert_notes(conn)
        await insert_action_items(conn)
        await insert_calendar_events(conn)
        await insert_decisions(conn)
        await insert_context_events(conn)
        await insert_thoughts(conn)
        await insert_semantic_entries(conn)
        await insert_entity_relationships(conn)
        await insert_note_associations(conn)
        await insert_note_metadata(conn)
        await insert_commitments(conn)
        await insert_connections(conn)

    await engine.dispose()

    print()
    print("Seeding complete!")
    print()
    print("Summary:")
    print("  1 user")
    print("  7 people")
    print("  4 projects")
    print("  15 vault notes (with rich content)")
    print("  10 action items")
    print("  6 calendar events")
    print("  4 decisions")
    print("  30 context events")
    print("  6 thoughts")
    print("  16 semantic entries")
    print("  11 entity relationships")
    print("  16 note associations")
    print("  15 note metadata records")
    print("  4 commitments")
    print("  6 connections")


if __name__ == "__main__":
    asyncio.run(seed())
