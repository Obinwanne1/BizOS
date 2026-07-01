# BizOS — React Migration Map

When ready to migrate from Streamlit to a production React frontend, this document maps every Streamlit page to its Next.js App Router equivalent.

The backend stays Python throughout. Migration strategy: build a Flask API layer on top of `orchestrator/` and `agents/`, then replace Streamlit pages with Next.js components one by one. Streamlit can stay running in parallel during migration.

---

## Architecture After Migration

```
bizos/
├── api/                        ← NEW: Flask API wrapping orchestrator + agents
│   ├── app.py                  Flask entry point
│   ├── routes/
│   │   ├── agents.py           POST /api/agents/{name}/run
│   │   ├── approvals.py        GET/POST /api/approvals
│   │   ├── workflows.py        POST /api/workflows/{name}/run
│   │   ├── crm.py              GET /api/crm/stats, /api/crm/leads
│   │   ├── memory.py           GET/POST/DELETE /api/memory
│   │   ├── chat.py             POST /api/chat (SSE stream)
│   │   └── analytics.py        GET /api/analytics
│   └── streaming.py            SSE helper for agent streaming
├── web/                        ← NEW: Next.js 14 App Router frontend
│   ├── app/
│   │   ├── layout.tsx          Root layout, sidebar nav, approval badge
│   │   ├── page.tsx            → app.py (Command Center)
│   │   ├── approvals/page.tsx  → 01_approvals.py
│   │   ├── agents/page.tsx     → 02_agents.py
│   │   ├── crm/page.tsx        → 03_crm.py
│   │   ├── content/page.tsx    → 04_content.py
│   │   ├── analytics/page.tsx  → 05_analytics.py
│   │   ├── memory/page.tsx     → 06_memory.py
│   │   ├── workflows/page.tsx  → 07_workflows.py
│   │   └── chat/page.tsx       → 08_chat.py
│   └── components/
│       ├── AgentCard.tsx
│       ├── ApprovalCard.tsx
│       ├── StreamingOutput.tsx
│       ├── WorkflowRunner.tsx
│       ├── ChatThread.tsx
│       └── FunnelChart.tsx
└── orchestrator/               unchanged
└── agents/                     unchanged
```

---

## Page-by-Page Mapping

### `dashboard/app.py` → `web/app/page.tsx`

**Streamlit:** Metrics row, pending approvals list, quick-run buttons, sidebar with approval badge.

**React equivalent:**
- `app/page.tsx` — Next.js App Router page (Server Component for initial data, Client Component for real-time badge)
- `<MetricsRow />` — 4-column stat cards, data from `GET /api/analytics`
- `<PendingApprovalsList />` — maps pending approvals; each card has Approve/Reject buttons calling `POST /api/approvals/{id}/approve`
- `<QuickRunBar />` — 6 buttons, each calls `POST /api/agents/{name}/run`, result shown in toast
- Sidebar approval badge: React `useQuery` polling every 15s → `GET /api/approvals?status=pending&count=true`

---

### `01_approvals.py` → `web/app/approvals/page.tsx`

**Streamlit:** Tabbed view (pending / history), per-agent rich preview, approve/reject with feedback.

**React equivalent:**
- `<ApprovalCard agent="content" preview={...} />` — per-agent rich rendering; content shows draft text area, sales shows email preview, lead_gen shows data table
- `<ApprovalActions />` — feedback textarea + Approve/Reject buttons
- Optimistic update: mark card as "processing" immediately, revert on error
- Real-time: SSE subscription to `GET /api/approvals/stream` — new approval triggers toast notification

---

### `02_agents.py` → `web/app/agents/page.tsx`

**Streamlit:** Agent grid, Run buttons, streaming output per agent.

**React equivalent:**
- `<AgentCard />` — label badge, description, schedule, last-run timestamp, Run button
- Streaming: `POST /api/agents/{name}/run` returns `Content-Type: text/event-stream`
- `<StreamingOutput />` — consumes SSE stream, appends tokens to a `<pre>` with auto-scroll
- After stream ends, status line appears: "Awaiting approval" or "Done"
- Use **Vercel AI SDK** `useChat()` pattern or raw `EventSource` for SSE consumption

**Key React library:** `@microsoft/fetch-event-source` for SSE with POST body support.

---

### `03_crm.py` → `web/app/crm/page.tsx`

**Streamlit:** Metrics, uncontacted leads table, Plotly funnel with drill-down.

**React equivalent:**
- `<FunnelChart />` — Recharts `FunnelChart` or Nivo `ResponsiveFunnel`; click event calls `GET /api/crm/leads?stage={stage}` and renders drill-down table below
- `<LeadsTable />` — React Table (TanStack Table) with sort/filter, pagination
- `<EmptyState />` — reusable empty state component with icon + CTA button

---

### `04_content.py` → `web/app/content/page.tsx`

**Streamlit:** Content feed showing approved posts, platform filter.

**React equivalent:**
- `<ContentFeed />` — card grid, filter by platform (LinkedIn / Twitter / Instagram)
- `<ContentCard />` — shows hook, body, hashtags, suggested time; copy-to-clipboard button
- Data: `GET /api/content?platform={p}&limit=20`

---

### `05_analytics.py` → `web/app/analytics/page.tsx`

**Streamlit:** Bar chart (activity by agent), line chart (daily activity), log table.

**React equivalent:**
- `<ActivityByAgent />` — Recharts `BarChart` with brand colors
- `<DailyActivityLine />` — Recharts `LineChart` with markers
- `<ActivityLog />` — TanStack Table, sortable, client-side filter
- Data: `GET /api/analytics/logs?limit=200` — no polling needed (historical data)

---

### `06_memory.py` → `web/app/memory/page.tsx`

**Streamlit:** Filter by agent/type, inline edit, delete, add memory form.

**React equivalent:**
- `<MemoryList />` — virtualized list (react-window for large sets), accordion per memory
- Inline edit: click value → `<textarea>` appears → Save calls `PATCH /api/memory/{id}`
- Delete: confirmation popover before `DELETE /api/memory/{id}`
- `<AddMemoryForm />` — agent select, type select, key/value inputs
- Data: `GET /api/memory?agent={a}&type={t}`

---

### `07_workflows.py` → `web/app/workflows/page.tsx`

**Streamlit:** Workflow cards with step arrows, Run button, history tab.

**React equivalent:**
- `<WorkflowCard />` — name, description, step chain rendered as `Step → Step → Step` with React Flow nodes (optional: `reactflow` package for visual DAG)
- `<WorkflowRunner />` — Run button → `POST /api/workflows/{name}/run`; shows step-by-step progress as SSE stream from backend
- `<WorkflowHistory />` — table of past runs, expandable step breakdown
- React Flow integration (optional): drag-and-drop workflow builder for custom pipelines

---

### `08_chat.py` → `web/app/chat/page.tsx`

**Streamlit:** Chat thread, streaming responses, voice input/output, quick actions.

**React equivalent:**
- **Vercel AI SDK** `useChat()` hook — handles streaming, message history, input state
- Backend: `POST /api/chat` returns SSE stream; each chunk is a token delta
- `<ChatMessage role="user|assistant" />` — markdown rendering via `react-markdown`
- `<VoiceInput />` — Web Speech API button, transcript populates input field directly (no iframe needed — full DOM access in React)
- `<VoiceSpeaker />` — SpeechSynthesis for ops briefing; triggered when assistant message from `operations` agent is complete
- `<QuickActions />` — pill buttons in sidebar inject preset prompts

---

## Flask API Layer (new `api/` folder)

Minimal Flask wrapper — no logic duplication, just HTTP surface:

```python
# api/routes/agents.py
from flask import Blueprint, Response, request, stream_with_context
from orchestrator.router import get_agent, dispatch_with_agent
import json

bp = Blueprint("agents", __name__)

@bp.route("/<agent_name>/run", methods=["POST"])
def run_agent(agent_name):
    payload = request.get_json() or {}

    def generate():
        chunks = []
        agent = get_agent(agent_name)
        agent._on_chunk = lambda delta: chunks.append(delta)  # non-blocking in SSE context
        # For true streaming: use threading.Thread + queue
        result = dispatch_with_agent(agent, agent_name, "api", payload)
        for chunk in chunks:
            yield f"data: {json.dumps({'type':'token','text':chunk})}\n\n"
        yield f"data: {json.dumps({'type':'done','status':result['status']})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")
```

For true parallel token streaming in Flask, use `queue.Queue` + `threading.Thread`:
- Thread runs `agent.run(payload)` with `_on_chunk` enqueuing chunks
- Main thread reads from queue in a generator, yields SSE events
- Sentinel value signals stream end

---

## Migration Order (recommended)

| Phase | What to build | Risk |
|-------|---------------|------|
| 1 | Flask API layer + `/api/agents`, `/api/approvals` routes | Low — no UI change |
| 2 | `web/` Next.js scaffold + `app/layout.tsx` (sidebar, nav) | Low |
| 3 | Chat page (`/chat`) — highest value, cleanest SSE fit | Medium |
| 4 | Agents page (`/agents`) with streaming | Medium |
| 5 | Approvals page (`/approvals`) + real-time SSE notifications | Medium |
| 6 | Remaining pages (CRM, Analytics, Memory, Workflows) | Low |
| 7 | Decommission Streamlit | Final |

---

## Key Libraries for React Build

| Need | Library |
|------|---------|
| Framework | Next.js 14 (App Router) |
| AI streaming | Vercel AI SDK (`ai` package) |
| Charts | Recharts (bar/line) + Nivo (funnel) |
| Tables | TanStack Table v8 |
| Workflow DAG | React Flow |
| SSE client | `@microsoft/fetch-event-source` |
| Markdown | `react-markdown` + `remark-gfm` |
| Styling | Tailwind CSS (brand: `#407E3C`) |
| State | Zustand (lightweight, no Redux overhead) |
| Data fetching | TanStack Query (useQuery / useMutation) |

---

## Brand Token Map (Tailwind)

```js
// tailwind.config.js
theme: {
  extend: {
    colors: {
      brand: {
        DEFAULT: '#407E3C',
        light:   '#5a9e56',
        pale:    '#e8f5e9',
      }
    }
  }
}
```
