# AI Usage Monitor

This repository contains a lightweight AI observability testbed for tracking usage, prompt activity, PII exposure, and agent governance drift across a small local deployment. The app is intentionally separate from the root Betty project and is designed to demonstrate how a monitoring layer can record sanitized activity without pretending to be a production-grade enterprise governance system.

## Project goals

- Capture prompt and model metadata from an AI gateway path
- Trace agent runs and compare declared vs observed data sources
- Redact or count common PII patterns before storage
- Surface usage analytics in a browser-based dashboard
- Provide a realistic local demo environment for evaluation and testing

## Stack

- Backend: Python + FastAPI
- Database: PostgreSQL-first configuration with SQLite fallback for local demo use
- Frontend: React + Vite
- Observability: OpenTelemetry FastAPI and HTTPX instrumentation plus custom gateway tracing spans
- Testing: pytest regression suite and frontend Vitest smoke tests

## Directory layout

```text
ai-usage-monitor/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── observability/
│   │   └── services/
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── docs/
│   └── capability-matrix.md
├── README.md
└── docker-compose.yml
```

## Data flow overview

```text
Client / support app
        |
        v
POST /chat or /agent/run
        |
        v
FastAPI app
  - redacts prompt text and detects PII
  - records sanitized prompt logs
  - wraps agent tool calls and source access
  - emits OpenTelemetry spans
        |
        +----------+----------------------------+
        |                                        |
        v                                        v
LLM gateway / upstream provider         SQLite/PostgreSQL database
  - filters secret headers                 - prompt_logs table
  - records model + token metadata         - access_events table
  - captures latency and status            - agent_runs table
        |                                        |
        v                                        v
Dashboard /analytics + /prompts + /runs -> Browser UI
```

## Clean install and startup

From the repository root:

```bash
cd ai-usage-monitor/backend
python -m venv .venv
. .venv/Scripts/activate   # Windows
# or: source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

Start PostgreSQL if desired:

```bash
cd ..
docker compose up -d db
```

If PostgreSQL is unavailable, the app automatically falls back to SQLite for local demo runs.

Run the backend:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Run the frontend:

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 3000
```

Open the UI at http://localhost:3000 and the API at http://localhost:8000/docs.

## Main endpoints

- `POST /chat` — demo chat endpoint with PII sanitize/redact flow
- `POST /agent/run` — runs a synthetic agent with declared vs observed sources
- `GET /dashboard/summary` — basic event summary
- `GET /dashboard/usage` — recent usage events
- `GET /dashboard/analytics` — usage over time, model usage, tokens, latency, failure rate, asset comparison, agent runtime summary
- `GET /dashboard/prompts` — sanitized prompt browsing and filtering
- `GET /dashboard/runs` — agent execution records

## Evaluator notes

This monitor is intentionally a realistic demo/testbed, not a production security product. The code is structured to support honest evaluation of the following:

- what the gateway can observe
- what is stored locally after redaction
- what triggers agent governance mismatch warnings
- what the dashboard can show from real execution data

## Privacy and governance boundary

- Raw prompt text is not stored in the local database.
- PII counts and sanitized prompts are stored instead.
- Tool arguments and prompt traces are sanitized before persistence.
- The gateway still forwards the original prompt to the configured upstream AI provider. That is a real limitation of any proxy architecture and is explicitly documented here.
- Access control is optional and demo-only. It is not a production authorization model.

## PII detection limits

The project supports best-effort detection for:

- email addresses
- phone numbers
- PAN/Aadhaar-like identifiers
- common credit-card patterns

It does not guarantee dependable identity resolution for all names or all real-world text. Name detection may miss weakly contextual names or produce false positives for capitalized words and organizations.

## Deployment and repo status

- Deployment: local Docker Compose and FastAPI/Vite startup workflow are supported for development and evaluation.
- Public repository: this project is not yet published as a public GitHub repository in this workspace snapshot, so no public link is included here.

## Verification commands

Run the backend tests from the backend folder:

```bash
pytest -q
```

Run the frontend tests:

```bash
cd frontend
npm install
npm test
```

The documented verification path is intentionally simple enough to reproduce on a clean local install.

## Known limitations

- Gateway protection is lightweight and not production hardened.
- PII detection is heuristic and should not be treated as a definitive identity classifier.
- Instrumentation only captures events that pass through the implemented wrappers and spans.
- This project is suitable as a monitoring demo and evaluation artifact, not as a full enterprise AI governance platform.
