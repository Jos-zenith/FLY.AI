# AI Usage Monitor

This repository contains a lightweight AI observability testbed for tracking usage, prompt activity, PII exposure, and agent governance drift across a small local deployment. The app is intentionally separate from the root Betty project and is designed to demonstrate how a monitoring layer can record sanitized activity without pretending to be a production-grade enterprise governance system.

## Project goals

- Capture prompt and model metadata from an AI gateway path
- Trace agent runs and compare declared vs observed data sources
- Redact or count common PII patterns before storage
- Surface usage analytics in a browser-based dashboard
- Provide a realistic local demo environment for evaluation and testing

## The one flow to follow

Everything else in this repo supports a single end-to-end story. Follow it in this order and nothing else needs digging up:

1. **A user enters a prompt containing PII** — open the app at `http://localhost:3000`, type a prompt with an email, phone number, or card number (or click one of the example prompts), and send it. Backend: `POST /chat` in [`backend/app/main.py`](backend/app/main.py).
2. **The system detects and redacts it** — the regex + Luhn-checked detector in [`backend/app/services/pii.py`](backend/app/services/pii.py) finds the PII spans and replaces them with `<TYPE>` markers before anything is written to disk.
3. **The sanitized prompt gets stored** — [`backend/app/services/prompt_capture.py`](backend/app/services/prompt_capture.py) persists the redacted text plus structured PII counts to the `prompt_logs` table. The raw text is never written.
4. **The model/gateway interaction happens** — the raw (unredacted) prompt still goes to the configured LLM/gateway client in `backend/app/services/llm_client.py`, exactly as it would in a real deployment. This is the gap the whole project exists to make visible — see "Privacy and governance boundary" below.
5. **The dashboard shows metrics and findings** — the same page redirects to the Overview tab, where "Just captured" shows exactly what was redacted, and the Prompts tab lists it as a searchable, exportable row.
6. **An agent run shows declared vs. observed mismatch** — run `python backend/scripts/seed_demo_data.py` (or `POST /agent/run` with `"query_orders": true`) and open the Agent Runs tab: a clean run shows "Within scope," a scope-breach run shows an amber "Scope violation: Orders DB" pill next to the source it touched but never declared.

Steps 1-5 take under a minute by hand in the running app. Step 6 is one script run. There is no other path through this repo that matters more than this one.

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
│   ├── vite.config.js
│   └── .env.example
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
- names, via two layers described below

**Names are detected two ways, and which one runs depends on what's installed.** An optional NER pipeline (`dslim/bert-base-NER` via `transformers`) gives the more accurate result, but it needs a model backend (`torch` or `tensorflow`) that is **not** pinned in `requirements.txt` — pulling in a multi-hundred-MB deep learning framework by default would make a from-scratch install of a demo project needlessly heavy. On a plain `pip install -r requirements.txt`, `get_ner()` fails to load (caught, logged once, never retried — see `services/pii.py`) and the app falls back to a **trigger-word regex heuristic**: it matches a capitalized word or two directly after `to` / `for` / `dear` / `hi` / `hello` / `regards` / `from`, which is exactly what makes this repository's own headline example work out of the box:

```
"Write a reminder email to Ramesh, phone 9840123456."
→ "Write a reminder email to <NAME>, phone <PHONE>."
```

This heuristic is intentionally narrow, and its failure modes are known and tested (`tests/test_pii.py`):
- **False negative**: a name with no trigger word in front of it is missed entirely — "call Ramesh back" does not redact "Ramesh".
- **False positive**: a capitalized non-name after a trigger word gets redacted anyway — "Grant access to Production" redacts "Production" as a name.

If `torch` is installed, the NER pipeline takes over and both cases improve, since it reasons about context rather than trigger words. Both layers can produce false positives for capitalized organization names, and neither guarantees dependable identity resolution for all real-world text — this is a best-effort detection layer, not a production identity-classification system.

A Luhn checksum guards the credit-card pattern specifically, since a bare 13-16 digit regex alone flags order numbers and tracking IDs as card numbers far too often.

Every detection is stored as structured metadata alongside the sanitized text, not just inline redaction markers — e.g. a prompt containing an email and a phone number is stored as `sanitized_prompt: "Contact <EMAIL> or <PHONE>"` with `pii_detected: {"EMAIL": 1, "PHONE": 1}`. The Prompts and Overview tabs read this metadata directly, so the dashboard can show *what kind* of PII was caught, not just that something was.

## Assumptions

- The environment generating AI activity does not need to be a real production app — a small FastAPI testbed that drives real `/chat` and `/agent/run` calls is sufficient to demonstrate the monitoring problem, per the brief's own framing ("The environment is only the testbed for the problem").
- An AI agent framework (LangGraph/LangChain) is not required. `/agent/run` demonstrates declared-vs-observed source tracking without one, and the brief explicitly allows this ("completely acceptable for the project to be built without any AI agent"). Adding LangGraph here would add a dependency without adding governance signal, since the thing being measured is data-source access, not multi-step reasoning.
- A single local demo user is assumed; there is no multi-tenant user model. Access control (API key/bearer) is optional and off by default, since the brief prioritizes engineering quality and monitoring accuracy over building a production auth system.
- "Realistic AI activity" means recognizable customer-support/billing-agent scenarios with real PII patterns and a genuine scope-violation case, not high request volume. The seed script produces a handful of high-signal events rather than thousands of synthetic rows.
- PostgreSQL is assumed to be the target database; SQLite is a fallback for zero-setup local evaluation only, not a supported production path.

## Key technical decisions

- **Hand-rolled regex + Luhn + optional NER for PII, not a third-party PII SDK.** This keeps the detection logic auditable in ~150 lines instead of hidden behind an opaque service, which matters more for a project whose subject *is* explaining detection capability and limitation honestly.
- **Structured PII metadata (`{"EMAIL": 1, "PHONE": 1}`) stored alongside sanitized text, not just inline markers.** Inline markers alone would make "which AI assets see the most PII" an expensive text-parsing query instead of a `GROUP BY`.
- **Declared-vs-observed tracking via a context manager (`AgentRunContext`), not middleware or decorators.** The access pattern (`record_access("Orders DB")` called from inside the agent's own code path) mirrors how a real team would instrument an existing agent with minimal invasiveness, which is the same shape gateway/OTel instrumentation takes in `docs/capability-matrix.md`.
- **The capability matrix was built by actually implementing each layer (no-app-changes, gateway, application instrumentation) against this same testbed, not by reasoning about them abstractly.** The "what's not visible" column in that matrix reflects what each layer's code in this repo genuinely cannot see, not a textbook claim.
- **No agent framework.** See Assumptions above — LangGraph/LangChain were evaluated and deliberately not used, since the governance question this project answers (did the agent touch an undeclared source) doesn't require an LLM-driven planning loop.

## Deployment and repo status

- Repository: https://github.com/Jos-zenith/FLY.AI — confirm this is set to **Public** under Settings → General → Danger Zone before submitting, since a private repo an evaluator can't open counts against "Public GitHub repository."
- Deployed: backend on Render (`https://fly-ai-dgsd.onrender.com`), frontend on Vercel (`https://vict-ai.vercel.app`).

### Deploying (Render backend + Vercel frontend)

Two environment variables connect the two deployed halves, and both are easy to get half-right:

1. **Render (backend) → `CORS_ALLOWED_ORIGINS`.** Comma-separated list of every frontend origin allowed to call this API — see `backend/.env.example`. It must be the deployed Vercel URL exactly (scheme + host, no trailing slash), or every request from the live frontend fails CORS preflight with `No 'Access-Control-Allow-Origin' header is present`. A Vercel *preview* deployment (e.g. a PR branch) gets its own random subdomain and needs adding here too if preview builds should reach the API.
2. **Vercel (frontend) → `VITE_API_URL`.** Set to the Render backend URL — see `frontend/.env.example`. Two things trip this up specifically:
   - **Vite only inlines env vars at build time.** `src/App.jsx` falls back to the deployed Render URL if `VITE_API_URL` is unset, so a build without it still points somewhere real instead of `localhost:8000` — but if you add or change the variable in Vercel's project settings, the *already-deployed* site does not pick it up until a new build runs. Vercel → Deployment Overview → `...` next to Visit → **Redeploy**.
   - **No hardcoded `localhost` URLs in frontend code.** `API_URL` in `src/App.jsx` is the single source of truth for the API base URL — grep for `localhost:8000` before deploying if you've copy-pasted a `fetch(...)` call anywhere else.

If you see a CORS error in the browser console after deploying, check these in order: (a) is the frontend actually calling the Render URL, not `localhost` — read the failing request's URL in the console, not just the error text; (b) does `CORS_ALLOWED_ORIGINS` on Render list that exact Vercel origin; (c) did Render actually restart after that env var was added (Render, like Vercel, doesn't hot-reload env var changes into a running service).

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
