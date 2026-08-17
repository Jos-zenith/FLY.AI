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
