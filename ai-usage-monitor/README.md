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
│   ├── scripts/
│   │   └── seed_demo_data.py   # populates a clean run + a scope-violation run
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── testbed/
│   └── customer_support_demo.py   # synthetic customer-support scenario generator
├── docs/
│   ├── architecture.excalidraw   # editable diagram, open at excalidraw.com
│   └── capability-matrix.md      # zero-code vs gateway vs SDK observability comparison
├── README.md
└── docker-compose.yml
```

See [`docs/capability-matrix.md`](docs/capability-matrix.md) for the full zero-code / gateway / SDK-instrumentation observability comparison, and [`docs/architecture.excalidraw`](docs/architecture.excalidraw) for an editable version of the diagram below (drag-and-drop it onto [excalidraw.com](https://excalidraw.com)).

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

## Demo data

The dashboard starts empty. To populate it with a realistic scenario for a live demo or recorded walkthrough, run the seed script against the running backend:

```bash
cd backend
python scripts/seed_demo_data.py
```

This drives the real `/chat` and `/agent/run` endpoints (it does not write fake rows directly into the database), and produces:

- Several sanitized chat prompts across different AI assets, some carrying real PII (email, phone, credit card) so the PII governance donut and Prompts tab have genuine detections to show.
- One **clean** agent run — declared `FAQ DB`, and it only ever touches `FAQ DB`. Shows up in Agent Runs as "Within scope".
- One **scope-violation** agent run — declared `FAQ DB`, but the simulated customer message mentions an order, so the agent also queries `Orders DB`, a source it never declared. This is the exact failure mode from the Samsung ChatGPT case study this project is modeled on: an AI assistant reaching a data source nobody approved for it.

The Agent Runs tab renders this as a visual diff, not just a status line: the Observed row highlights the undeclared source inline with a warning icon, and an amber "Scope violation: Orders DB" pill sits next to the run.

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

It does not guarantee dependable identity resolution for all names or all real-world text. Name detection may miss weakly contextual names or produce false positives for capitalized words and organizations. A Luhn checksum guards the credit-card pattern specifically, since a bare 13-16 digit regex alone flags order numbers and tracking IDs as card numbers far too often.

Every detection is stored as structured metadata alongside the sanitized text, not just inline redaction markers — e.g. a prompt containing an email and a phone number is stored as `sanitized_prompt: "Contact <EMAIL> or <PHONE>"` with `pii_detected: {"EMAIL": 1, "PHONE": 1}`. The Prompts and Overview tabs read this metadata directly, so the dashboard can show *what kind* of PII was caught, not just that something was.

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
