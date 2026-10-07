# White Vision Event Portal

A private customer portal for White Vision, a Dutch DJ & event entertainment company.
Each customer gets a personal event environment (dashboard, chat with their DJ, music
wishes, run-of-show timeline, invitation builder, guest RSVPs and files). White Vision
staff (admin + DJs) get a separate admin area to create customers/events and manage
everything. The UI is in Dutch.

> Supersedes the original MongoDB/Motor/GridFS implementation — see `memory/PRD.md`.

## Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI, SQLAlchemy 2.0 (async), asyncpg, Alembic |
| Database | PostgreSQL (UUID keys, JSONB, `BYTEA` for uploaded files) |
| Auth | JWT in httpOnly cookies (15 min access / 7 day refresh), bcrypt |
| Frontend | React (CRA + CRACO), Tailwind, shadcn/Radix, React Router |

## Layout

```
backend/            FastAPI app
  server.py         entry point (mounts every router under /api)
  database.py       async engine, session, Base
  core.py           auth, role checks, event scoping
  models.py         SQLAlchemy ORM tables
  schemas.py        Pydantic request/response models
  services.py       derived data (progress/stats/enrichment)
  routes/           one module per domain
  seed.py           admin bootstrap, template reference data, optional demo data
  alembic/          migrations
frontend/           React app (src/features are reused by customer and admin)
docker-compose.yml  local PostgreSQL 16
```

## Local setup

1. **Database** — either `docker compose up -d`, or use a local Postgres and create a
   role/database matching `DATABASE_URL`.
2. **Backend**
   ```bash
   cd backend
   cp .env.example .env          # then fill in values (see below)
   pip install -r requirements.txt
   alembic upgrade head
   uvicorn server:app --reload --port 8001
   ```
   On startup the app creates the admin user and the invitation templates. Demo
   customers/events are only seeded when `SEED_DEMO=true`.
3. **Frontend**
   ```bash
   cd frontend
   cp .env.example .env          # set REACT_APP_BACKEND_URL
   npm install
   npm start
   ```

## Environment

`backend/.env` (see `backend/.env.example`):

- `DATABASE_URL` — asyncpg URL; add `?ssl=require` for a managed database.
- `JWT_SECRET` — at least 32 random bytes.
- `CORS_ORIGINS` — exact frontend origin(s), comma separated.
- `FRONTEND_URL` — used for reset/welcome links; **must be https** (the email guard
  rejects non-https links).
- `ADMIN_EMAIL` / `ADMIN_PASSWORD` — bootstrap admin; created once, never overwritten.
- `SEED_DEMO` — `false` in production; `DEMO_PASSWORD` only needed when it's `true`.
- `WP_API_KEY` — key for `POST /api/integrations/wordpress/sync`.
- `EMERGENT_EMAIL_KEY` / `EMAIL_FROM_NAME` — transactional email.

`frontend/.env`: `REACT_APP_BACKEND_URL` (build-time; without it the API base is
`undefined/api`).

## Tests

```bash
cd backend
python -m pytest -n 0          # serial — the reliable mode
```

The suite hits a running backend and a seeded database. It mutates one shared dataset
(`sanne`'s password, `jeroen`'s event) across modules/classes, so run it serially; the
`-n 2` xdist default in `pytest.ini` can race on those shared rows.

## Deploy checklist

- [ ] Provision PostgreSQL; set `DATABASE_URL` (with TLS).
- [ ] Set strong `JWT_SECRET`, `ADMIN_PASSWORD`, `WP_API_KEY`.
- [ ] Set `CORS_ORIGINS` and `FRONTEND_URL` to the https production domain.
- [ ] `SEED_DEMO=false`.
- [ ] Run `alembic upgrade head` (or use `backend/entrypoint.sh`).
- [ ] Build the frontend with `REACT_APP_BACKEND_URL` set.
- [ ] Serve over HTTPS — auth cookies are `Secure`.
