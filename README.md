# Betty

This repository contains two different applications that should be treated as separate services:

- `backend/` + `frontend/` = the Betty starter app
- `ai-usage-monitor/` = the AI Usage Monitor observability testbed

The root Docker Compose and default app startup are for the Betty starter app only. The AI Usage Monitor is a separate project and should be started from its own folder.

## Betty starter app

A full-stack starter app with:

- Python + FastAPI backend
- PostgreSQL database via Docker Compose
- React frontend with Vite

### Stack

- Backend: FastAPI, SQLAlchemy, PostgreSQL
- Frontend: React + Vite
- Database: PostgreSQL 16

### Quick start

1. Start PostgreSQL:
   ```bash
   docker compose up -d db
   ```

2. Set up the backend virtual environment:
   ```bash
   cd backend
   python -m venv .venv
   . .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Run the backend:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. In another terminal, start the frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. Open the frontend at http://localhost:3000

### Docker Compose

To run everything together:

```bash
docker compose up --build
```

### Default database connection

The Betty app expects PostgreSQL at:

- Host: localhost
- Port: 5432
- Database: betty
- User: postgres
- Password: postgres

The backend reads from `backend/.env` or the environment variable `DATABASE_URL`.

## AI Usage Monitor

The AI monitor is a separate application located under `ai-usage-monitor/` and should not be started with the root Betty frontend/backend commands.

### Start the AI monitor with PostgreSQL

From the `ai-usage-monitor` folder:

```bash
docker compose up -d db
cd backend
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

In a second terminal:

```bash
cd ai-usage-monitor/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 3000
```

The AI monitor is PostgreSQL-first by default, and its database should be:

- Host: localhost
- Port: 5432
- Database: ai_usage_monitor
- User: postgres
- Password: postgres

If Postgres is unavailable, the app falls back to local SQLite for developer convenience, but the intended production-style setup is PostgreSQL.
