AI Usage Monitor — VICT.AI Submission

This repository is a submission for VICT.AI's AI Usage Monitoring & Governance challenge, "Watching How AI Is Actually Used": build a proof of concept that safely observes real AI activity, sanitizes sensitive information before it is ever stored, and reconciles what an AI agent was declared to do against what it actually did — the same gap that let Samsung employees paste confidential source code into ChatGPT in 2023 with nothing in between to notice.

The primary, evaluated application is ai-usage-monitor/. Its own README has the full write-up — architecture and data flow, the PII detection approach and its limits, the no-code/gateway/code-instrumentation capability matrix, assumptions, and known limitations.

The reasoning behind what got built and in what order — grounded in the 2023 Samsung–ChatGPT case, three user personas (an engineer who never opens the dashboard, a governance lead who needs evidence not a shrug, and a backend engineer who needs an honest capability matrix), their journey maps, and the Priority–Impact matrix that separated the quick wins from the major projects — is written up separately: Design Strategy Document.

Running the AI Usage Monitor
bash
cd ai-usage-monitor/backend
python -m venv .venv
. .venv/Scripts/activate   # Windows
# or: source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

In a second terminal:

bash
cd ai-usage-monitor/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 3000

Open the dashboard at http://localhost:3000 and the interactive API docs at http://localhost:8000/docs.

The app is PostgreSQL-first by default — ai-usage-monitor/docker-compose.yml starts a local Postgres instance. If PostgreSQL isn't available, it falls back to local SQLite automatically, so the whole thing still runs with zero external services configured.

To see the dashboard populated with realistic activity instead of an empty state — sample prompts carrying real PII, a clean agent run, and a scope-violation agent run — run the seed script from a third terminal once both servers are up:

bash
cd ai-usage-monitor/backend
python scripts/seed_demo_data.py

For everything else — directory layout, the end-to-end data flow, main endpoints, the PII detection approach and its limits, the observability exporter, and known limitations — see ai-usage-monitor/README.md.

A standalone FastAPI + PostgreSQL + React starter scaffold kept in this repository as a separate demo project, unrelated to AI usage monitoring. See betty-starter-app/ for its own setup (docker-compose up --build from that folder).
