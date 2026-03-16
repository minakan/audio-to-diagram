# audio-to-diagram

Real-time instructional speech visualization system for programming labs.

## Architecture

- Frontend: Next.js (TypeScript)
- Backend: FastAPI (Python)
- Realtime transport: WebSocket (`/ws/audio`)
- Intermediate representation: `diagram_plan`
- SVG output: sanitized SVG only
- Database: PostgreSQL (Docker service)

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: `http://localhost:3000`
- Backend health: `http://localhost:8000/health`
- WebSocket: `ws://localhost:8000/ws/audio`

## Local backend (uv)

```bash
cd backend
uv sync --extra dev
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Local tests

```bash
cd backend
uv sync --extra dev
uv run pytest
```
