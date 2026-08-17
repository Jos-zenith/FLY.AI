# Betty

A full-stack starter app with:

- Python + FastAPI backend
- PostgreSQL database via Docker Compose
- React frontend with Vite

## Stack

- Backend: FastAPI, SQLAlchemy, PostgreSQL
- Frontend: React + Vite
- Database: PostgreSQL 16

## Quick start

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

## Docker Compose

To run everything together:

```bash
docker compose up --build
```

## Default database connection

The app expects PostgreSQL at:

- Host: localhost
- Port: 5432
- Database: betty
- User: postgres
- Password: postgres

The backend reads from `backend/.env` or the environment variable `DATABASE_URL`.
