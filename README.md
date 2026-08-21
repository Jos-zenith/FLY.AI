# AI Usage Monitor (this repo's primary app)

This repository's primary, evaluated application is `ai-usage-monitor/` — the AI usage monitoring and governance proof of concept described in `docs/`.

An unrelated full-stack starter scaffold (`betty-starter-app/`) also lives in this repo as a separate example app. It is not part of the AI Usage Monitor and does not need to be running to evaluate it.

## Running the AI Usage Monitor

```bash
cd ai-usage-monitor/backend
python -m venv .venv
. .venv/Scripts/activate   # Windows
# or: source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

In a second terminal:

```bash
cd ai-usage-monitor/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 3000
```

Open the dashboard at http://localhost:3000 and the API at http://localhost:8000/docs.

The AI monitor is PostgreSQL-first by default (`ai-usage-monitor/docker-compose.yml` starts a local Postgres). If PostgreSQL is unavailable, the app falls back to local SQLite automatically so it can still be run without a database service.

See `ai-usage-monitor/README.md` for full details: directory layout, data flow, main endpoints, PII detection limits, and known limitations.

## `betty-starter-app/` (separate, unrelated example)

A standalone FastAPI + PostgreSQL + React starter app kept in this repo as a separate demo, unrelated to AI usage monitoring. See `betty-starter-app/` for its own setup (`docker-compose up --build` from that folder).
