# AI Usage Monitor

A starter project for monitoring AI usage patterns, tracking agent behavior, detecting PII, and surfacing a dashboard for review.

## Stack

- Backend: Python + FastAPI
- Database: PostgreSQL
- Frontend: React + Vite
- Monitoring: OpenTelemetry-friendly observability hooks
- Testing: minimal pytest smoke tests

## Structure

- `backend/` contains the API, models, services, and DB configuration.
- `frontend/` contains the dashboard UI.
- `testbed/` contains a fake customer support app and fake data used to simulate usage.
- `docs/` contains architecture and capability notes.

## Local startup

1. Create and activate a backend venv.
2. Install dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
3. Start PostgreSQL locally or via Docker.
4. Run the API:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
5. Run the frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Main routes

- `POST /chat`
- `POST /agent/run`
- `GET /dashboard/summary`
- `GET /dashboard/usage`

## Prompt capture notes

- Prompts are sanitized before persistence.
- Stored metadata includes PII type counts only, never the raw prompt text.
- Prompt monitoring can be disabled per asset with `PROMPT_MONITORING_DISABLED_ASSETS`.
- Retention is controlled with `PROMPT_LOG_RETENTION_DAYS` and old records are purged automatically.
- Sanitized prompts remain searchable through the dashboard prompt listing.

## Known failure modes

- Regex can miss unstructured names like "call Ramesh" if the surrounding context is weak.
- NER can flag common capitalized words mid-sentence as names or organizations.
- Neither regex nor NER reliably detects PII hidden inside code snippets, base64 blobs, or similarly encoded text.

## Agent observability limits

- The app only sees tool calls and database accesses that flow through the wrappers in `app/services/agent_tracker.py`.
- If a library makes its own network or database call outside those wrappers, that access will not appear in `access_events`.
- Observed sources are derived from distinct `access_events.source_name` values, so nested internal reads may collapse into one visible source unless they are wrapped separately.
