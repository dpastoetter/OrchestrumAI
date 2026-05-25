# OpenMiniAgents

**Repository:** [github.com/dpastoetter/OpenMiniAgents](https://github.com/dpastoetter/OpenMiniAgents)

Long-running **Google ADK** workflow agents with a custom **React** UI to submit requests, approve plans, and track status.

## Agents

| Agent | What it does |
|-------|----------------|
| **General workflow** | Plan → human approval → execute any text goal |
| **Document → Google Sheets** | Upload PDF/CSV/XLSX/image → extract rows → review → append to a Sheet |

## Architecture

- **`agents/workflow_agent/`** — Generic ADK workflow agent
- **`agents/doc_to_sheets_agent/`** — Document extraction + Sheets export
- **`backend/openminiagents/`** — FastAPI (`web=False`), `/api/requests`, parsers, Sheets client
- **`frontend/`** — React UI with file upload and row preview table

Sessions: ADK `DatabaseSessionService` (SQLite). Request metadata: separate SQLite index.

## AI providers

Inspired by [BrowserOS](https://github.com/browseros-ai/BrowserOS), you can connect multiple LLM backends:

| Provider | Auth | Notes |
|----------|------|--------|
| Google Gemini | API key (`GOOGLE_API_KEY`) | Native ADK (default) |
| OpenAI | API key | Via LiteLLM |
| Claude (Anthropic) | API key | Via LiteLLM |
| OpenRouter | API key | Via LiteLLM |
| Ollama | Local host | No key |
| LM Studio | Local OpenAI-compatible URL | No key |
| ChatGPT Plus/Pro | OAuth (Codex) | Connect in Settings; tokens in `data/chatgpt_oauth.json` |

Open **AI providers** in the UI (`/settings`) to set the default model, paste API keys (stored locally in `data/llm_settings.json`), connect ChatGPT OAuth, or configure Ollama/LM Studio URLs.

Install LiteLLM + Codex OAuth for non-Gemini providers: `pip install 'openminiagents[llm]'`

## Requirements

- Python 3.11+
- Node.js 18+
- At least one LLM credential (or stub mode / Ollama) for agent runs
- [Gemini API key](https://aistudio.google.com/apikey) for best PDF/image extraction
- Google Cloud **service account** with Sheets API (optional for real writes; share target Sheet with the SA email)

## Quick start

```bash
pip install -e ".[dev]"
cd frontend && npm install
cp .env.example .env

# Terminal 1 — API (stub: no Gemini, mock Sheets writes)
export OPENMINIAGENTS_STUB_RUN=1
make dev-backend

# Terminal 2 — UI
make dev-frontend
```

Open [http://localhost:5173](http://localhost:5173). Choose **Document → Google Sheets**, upload a CSV, review the preview, then **Approve & write to Sheets**.

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
| GET | `/api/agents` | List available agents |
| POST | `/api/requests` | JSON submit (workflow or doc metadata) |
| POST | `/api/requests/upload` | Multipart: file + form fields (doc_to_sheets) |
| GET | `/api/requests` | List requests |
| GET | `/api/requests/{id}` | Detail + `preview_rows` for doc agent |
| POST | `/api/requests/{id}/resume` | Approve or reject |
| GET | `/api/requests/{id}/events` | SSE progress |

## Tests

```bash
make test
```

## Docs

- [ADK Python](https://google.github.io/adk-docs/)
- [Long-running agents with ADK](https://developers.googleblog.com/build-long-running-ai-agents-that-pause-resume-and-never-lose-context-with-adk/)
