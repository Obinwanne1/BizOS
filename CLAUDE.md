# BizOS — Claude Code Context

## What This Is
AI Business Operating System for a real estate SaaS startup.
6 specialized agents (Lead Gen, Content, Sales, Marketing, Product, Operations)
orchestrated under a Streamlit CEO dashboard with approval gates.

## Run
```
cd bizos
pip install -r requirements.txt
cp .env.example .env  # fill in API keys
streamlit run dashboard/app.py
```

## Architecture
- `orchestrator/state.py` — SQLite DB, task queue, approval queue
- `orchestrator/router.py` — dispatch tasks to agents
- `orchestrator/approval.py` — approve/reject + execute
- `agents/base.py` — BaseAgent class with Claude API agentic loop
- `agents/*.py` — 6 department agents
- `tools/*.py` — Airtable CRM, Google Workspace, Slack, Buffer, web research
- `dashboard/` — Streamlit CEO control center
- `config/agents.yaml` — agent personas, models, schedules
- `config/settings.yaml` — CRM stages, content types, limits

## Key Patterns
- Every agent returns `AgentResult(requires_approval=True/False)`
- Side-effect actions → approval queue → CEO approves → `execute_approved()` called
- Read-only actions (ops briefing) → auto-execute, no approval needed
- All tools have stub fallbacks when API keys not set

## Models
- Orchestrator: claude-opus-4-8
- Content/Sales/Lead Gen/Marketing/Product: claude-sonnet-4-6
- Operations: claude-haiku-4-5-20251001

## Tests
```
pytest tests/ -v
```

## Brand
- Primary: #407E3C | White | Accent: #5a9e56

## What's Connected (requires API keys in .env)
- Claude API: all agents
- Airtable: CRM (leads, deals)
- Google Workspace: Gmail drafts, Calendar, Drive
- Slack: CEO notifications
- Buffer: social media scheduling
- Apollo.io OR Hunter.io: lead enrichment

## What Stubs When Key Missing
All tools check for API keys and print stub output if absent.
System is fully functional in demo mode without any API keys.
