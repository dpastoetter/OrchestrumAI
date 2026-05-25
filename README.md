# OpenMiniAgents

**Repository:** [github.com/dpastoetter/OpenMiniAgents](https://github.com/dpastoetter/OpenMiniAgents)

Long-running **Google ADK** workflow agents with a custom **React** UI to submit requests, approve plans, and track status.

**License:** [MIT](LICENSE) — Copyright (c) 2026 Dominik Pastoetter

## Screenshots

| Requests | Submit (topology builder) |
|----------|-------------------------|
| ![Requests list](docs/screenshots/requests.png) | ![Submit with Simple / Sequential / Orchestrator canvas and specialist palette](docs/screenshots/submit.png) |

| Request detail (approval) | AI providers |
|---------------------------|--------------|
| ![Request detail with plan, topology chips, and approve/reject](docs/screenshots/request-detail.png) | ![Settings — default LLM, workflow agent defaults, ChatGPT OAuth](docs/screenshots/settings.png) |

Regenerate after UI changes (with `make dev-backend` and `make dev-frontend` running):

```bash
cd scripts && npm install && node capture-screenshots.mjs
```

## Features

- **Two built-in agents** — General workflow (any text goal) and Document → Google Sheets
- **Human-in-the-loop** — Plan and row-mapping steps pause for approval in the UI
- **Multi-provider LLM** — Gemini (native), OpenAI, Claude, OpenRouter, Ollama, LM Studio, ChatGPT OAuth
- **Per-request agent topology** — Drag-and-drop canvas on Submit to define how specialists work together
- **Workflow specialists** — Research (URL fetch), Writer, Editor; plus custom agents (name + instruction)
- **Stub mode** — Run the full UI without API keys (`OPENMINIAGENTS_STUB_RUN=1`)

## Agents

| Agent | What it does |
|-------|----------------|
| **General workflow** | State machine: submit → plan → approve → execute → complete. Execution layout is chosen per request on Submit (see below). |
| **Document → Google Sheets** | Upload PDF/CSV/XLSX/image → extract rows → review preview → approve → append to Google Sheets |

### Agent interaction (General workflow only)

On **Submit**, pick one of three topologies and arrange agents on the canvas (palette: Research, Writer, Editor, or **Custom**):

| Mode | Behavior |
|------|----------|
| **Simple** | One agent (catalog or custom) performs planning and execution; workflow tools stay on that root agent. |
| **Sequential** | Coordinator runs a **pipeline** tool: specialists execute in order (A → B → C). Reorder nodes on the canvas; edges link steps. |
| **Orchestrator** | Coordinator delegates during execution via **AgentTool** (same pattern as hub-and-spoke). Default: Research + Writer. |

Request detail shows the topology mode and agent names as chips. Older requests without topology may still list legacy `enabled_generic_agents` IDs.

**Settings → Workflow agents** still sets **default** enabled specialists for requests that do not send `agent_topology`. Per-request canvas overrides that for each new workflow submit.

## Architecture

```
agents/
  workflow_agent/          # Plan/approve/execute state machine + tools
    generic_agents/        # Research, Writer, Editor catalog
    topology.py            # Topology schema + validation
    topology_builder.py    # Builds LlmAgent / SequentialAgent / AgentTool graph
  doc_to_sheets_agent/     # Parse, preview, Sheets export

backend/openminiagents/    # FastAPI (ADK web=False), request store, runner bridge
frontend/                  # React + Vite + React Flow topology canvas
data/                      # llm_settings.json, workflow_settings.json, SQLite DBs
```

- **Sessions:** ADK `DatabaseSessionService` (SQLite under `data/`)
- **Request index:** SQLite (`data/requests.db`) — title, step, topology JSON, LLM choice, etc.
- **Runner cache:** Keyed by provider, model, and topology (or legacy enabled sub-agent list)

## AI providers

Connect backends from **Settings** (`/settings`):

| Provider | Auth | Notes |
|----------|------|--------|
| Google Gemini | API key (`GOOGLE_API_KEY`) | Native ADK (default) |
| OpenAI | API key | Via LiteLLM |
| Claude (Anthropic) | API key | Via LiteLLM |
| OpenRouter | API key | Via LiteLLM |
| Ollama | Local host | No key |
| LM Studio | Local OpenAI-compatible URL | No key |
| ChatGPT Plus/Pro | OAuth (Codex) | Connect in Settings; tokens in `data/chatgpt_oauth.json` |

Optional per-request override on Submit. Keys and defaults are stored locally in `data/llm_settings.json`.

```bash
pip install 'openminiagents[llm]'   # LiteLLM + Codex OAuth extras
```

If provider dropdowns stay empty, restart the backend so `/api/providers` is registered (`GET /api/health` should include a `features` array).

## Requirements

- Python 3.11+
- Node.js 18+
- At least one LLM credential (or stub mode / Ollama) for live agent runs
- [Gemini API key](https://aistudio.google.com/apikey) for best PDF/image extraction
- Google Cloud **service account** with Sheets API (optional for real writes; share the Sheet with the SA email)

## Quick start

```bash
pip install -e ".[dev]"
cd frontend && npm install
cp .env.example .env
```

**Terminal 1 — API** (stub: no Gemini, mock Sheets, simulated workflow):

```bash
export OPENMINIAGENTS_STUB_RUN=1
make dev-backend
```

**Terminal 2 — UI:**

```bash
make dev-frontend
```

Open [http://localhost:5173](http://localhost:5173).

- **General workflow:** Submit → pick topology → add agents on the canvas → describe the goal → approve when prompted.
- **Doc → Sheets:** Submit → upload a file → review the preview table → approve write.

Production-style single process (API serves built UI):

```bash
make build-frontend
# then start backend; open http://127.0.0.1:8000/
```

### Live runs

```bash
unset OPENMINIAGENTS_STUB_RUN
export GOOGLE_API_KEY=your-key
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
export DEFAULT_SPREADSHEET_ID=your-spreadsheet-id
make dev-backend
```

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Service status and feature flags (`providers`, `workflow`, …) |
| GET | `/api/agents` | List available agents |
| POST | `/api/requests` | JSON submit; workflow body may include `agent_topology` |
| POST | `/api/requests/upload` | Multipart file + fields (`doc_to_sheets`) |
| GET | `/api/requests` | List requests |
| GET | `/api/requests/{id}` | Detail, `preview_rows`, topology summary fields |
| POST | `/api/requests/{id}/resume` | `{ "decision": "approved" \| "rejected", "comment": "" }` |
| GET | `/api/requests/{id}/events` | SSE progress |
| GET | `/api/providers` | LLM catalog + saved settings |
| PUT | `/api/providers/settings` | Update default provider / keys / local URLs |
| POST | `/api/providers/test` | Connectivity check |
| GET/POST | `/api/providers/chatgpt-oauth/*` | ChatGPT OAuth connect / status / disconnect |
| GET | `/api/workflow/generic-agents` | Specialist catalog (palette metadata) |
| GET/PUT | `/api/workflow/settings` | Default enabled specialists (when no per-request topology) |

### `agent_topology` (workflow JSON body)

```json
{
  "type": "orchestrator",
  "nodes": [
    { "id": "n1", "kind": "catalog", "catalog_id": "research" },
    { "id": "n2", "kind": "custom", "name": "Reviewer", "instruction": "Check facts and tone." }
  ],
  "edges": []
}
```

Types: `simple` | `sequential` | `orchestrator`. Sequential requests may send `edges` as `{ "from": "n1", "to": "n2" }` chains; the UI auto-chains when reordering nodes.

## Tests

```bash
make test
```

Includes workflow generic agents, agent topology validation/build, and API integration tests.

## Docs

- [ADK Python](https://google.github.io/adk-docs/)
- [Long-running agents with ADK](https://developers.googleblog.com/build-long-running-ai-agents-that-pause-resume-and-never-lose-context-with-adk/)

## Author

Dominik Pastoetter — [github.com/dpastoetter](https://github.com/dpastoetter)
