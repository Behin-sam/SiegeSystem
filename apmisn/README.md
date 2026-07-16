# Autonomous Multi-Region Payment & Identity Settlement Network

Enterprise-grade project **foundation** — architecture, tooling, and scaffolding only.
No payment, settlement, or identity **business logic** has been implemented yet; this
repository is the compiling, runnable base the next phases build on top of.

## Tech stack

| Layer      | Choices |
|------------|---------|
| Frontend   | Next.js 15 (App Router), TypeScript, Tailwind CSS, shadcn/ui, React Query, Framer Motion |
| Backend    | FastAPI, PostgreSQL, SQLAlchemy 2.0 (async), Redis |
| Auth       | JWT (access + refresh tokens), bcrypt password hashing |
| Infra      | Docker, Docker Compose |

## Repository layout

```
apmisn/
├── docker-compose.yml        # orchestrates db, redis, backend, frontend
├── .env.example               # root env vars consumed by docker-compose
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/                # migration environment (no migrations generated yet)
│   ├── tests/                  # smoke tests (pytest)
│   └── app/
│       ├── main.py             # FastAPI app factory, middleware, routers
│       ├── core/                # config, security, logging, exceptions
│       ├── db/                  # SQLAlchemy base + async session
│       ├── models/              # ORM models (User only, for auth)
│       ├── schemas/             # Pydantic request/response schemas
│       ├── api/v1/               # versioned routers + endpoints
│       ├── middleware/           # request logging, auth header checks
│       └── redis_client/         # Redis connection factory
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── tailwind.config.ts        # design tokens (see globals.css for HSL vars)
    └── src/
        ├── app/                  # App Router: /, /login, /dashboard/*
        ├── components/
        │   ├── ui/                # shadcn primitives (button, card, sheet, ...)
        │   ├── layout/            # Sidebar, Navbar, DashboardShell
        │   └── providers/         # ThemeProvider, QueryProvider
        ├── lib/                   # cn(), Axios client w/ refresh interceptor, token storage
        ├── hooks/                 # useLogin, useLogout, useCurrentUser
        └── types/                 # shared TS types mirroring backend schemas
```

## What's implemented

- **Folder structure** — clean separation of concerns on both sides (see tree above).
- **Docker setup** — multi-stage Dockerfiles for both services, `docker-compose.yml`
  wiring Postgres, Redis, backend, and frontend with healthchecks and a shared network.
- **Environment variables** — `.env.example` at root and in `backend/`; `frontend/.env.example`.
- **Backend architecture** — layered `core / db / models / schemas / api / middleware`
  structure; settings loaded once via a cached `pydantic-settings` singleton.
- **Frontend architecture** — App Router route groups (`(auth)`, `(dashboard)`), typed
  API client, React Query hooks, provider composition in `layout.tsx`.
- **Database connection** — async SQLAlchemy engine/session (`app/db/session.py`),
  Alembic environment pre-wired to the same settings and metadata.
- **Authentication middleware** — JWT access/refresh tokens (`app/core/security.py`),
  `get_current_user` FastAPI dependency, an Axios interceptor that transparently
  refreshes expired tokens on the frontend.
- **Error handling** — a single `AppError` hierarchy with consistent JSON error
  envelopes, registered via `register_exception_handlers`.
- **Logging** — structured JSON/console logging via `structlog`, request-scoped
  request IDs bound through `RequestLoggingMiddleware`.
- **API structure & routing** — versioned under `/api/v1`, routers aggregated in
  `app/api/v1/router.py` (`/health`, `/auth`, `/users`).
- **Theme** — light/dark HSL design tokens in `globals.css`, toggled via `next-themes`.
- **Responsive layout, Sidebar, Navbar, Dashboard shell** — see
  `src/components/layout/`. Sidebar collapses into a slide-over `Sheet` below `md`.

## Running locally with Docker

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend docs (Swagger): http://localhost:8000/api/v1/docs
- Backend health: http://localhost:8000/api/v1/health/live

## Running without Docker

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # point POSTGRES_HOST / REDIS_HOST at localhost if running services locally
uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

## Verified before hand-off

- `pip install -r backend/requirements.txt` succeeds; `app.main` imports cleanly;
  `pytest` smoke tests (`tests/test_health.py`) pass.
- `npm install` succeeds with no vulnerable dependency warnings; `npm run build`
  compiles, type-checks, and statically prerenders all routes (`/`, `/login`,
  `/dashboard`) with zero errors.

## Explicitly out of scope for this phase

Business/domain logic: settlement instructions, ledger reconciliation, identity
verification (KYC/KYB), regional routing rules, compliance workflows, and their
corresponding data models, endpoints, and UI. The `User` model and auth flow exist
only to prove out the authentication foundation.
