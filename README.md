# FusionBoard Backend

**Modular FastAPI backend with real-time WebSocket support, pluggable service architecture, and JWT authentication.**

Built with Python 3.12, FastAPI, SQLAlchemy 2.0, and PostgreSQL. Designed as the backbone for FusionBoard — a unified command center that aggregates multiple platform services.

---

## Table of Contents

- [Architecture](#architecture)
- [Module Overview](#module-overview)
- [API Reference](#api-reference)
- [Authentication](#authentication)
- [Real-time Features](#real-time-features)
- [Service Registry](#service-registry)
- [Database Models](#database-models)
- [Getting Started](#getting-started)
- [Deployment](#deployment)
- [Environment Variables](#environment-variables)

---

## Architecture

```
src/
├── modules/                    # Feature modules (pluggable)
│   ├── auth/                   # JWT login, logout, refresh, password change
│   ├── user/                   # User model (shared across modules)
│   ├── admin/                  # Admin model (inherits User via STI)
│   ├── football_tracking/      # Proxy to external Football API
│   ├── job_tracker/            # Job application CRUD + analytics
│   ├── smart_tasks/            # Task management with recurring support
│   ├── daily_brief/            # Aggregated dashboard summary
│   ├── platform_registry/      # Service discovery + health checks
│   ├── sample_platform/        # Copy-paste template for new services
│   ├── webhooks/               # Incoming webhook receiver
│   └── websocket/              # Connection manager + broadcasting
├── extensions/
│   ├── auth_jwt/               # Custom JWT implementation (cookies + headers)
│   ├── sqlalchemy/             # Engine, session middleware, URL builder
│   └── migrations/             # Alembic migration scripts
├── project_helpers/
│   ├── dependencies/           # Injectable dependencies (JWT validation, user extraction)
│   ├── error/                  # Standardized error codes (E0010–E0999)
│   ├── exceptions/             # Custom exception hierarchy
│   ├── functions/              # Password hashing utilities
│   ├── responses/              # Response wrapper helpers
│   └── schemas/                # Shared Pydantic schemas
├── constants/                  # Enums (ADMIN / PLAYER roles)
└── services/
    ├── run_api.py              # FastAPI app factory + lifespan
    └── run_migration.py        # Alembic migration runner
```

Each module follows the same convention:
```
module_name/
├── models/          # SQLAlchemy models
├── schemas/         # Pydantic request/response schemas
├── routes/          # FastAPI router + endpoint handlers
├── api_client.py    # External API integration (if applicable)
└── __init__.py      # Router export
```

---

## Module Overview

| Module | Prefix | Description |
|--------|--------|-------------|
| **auth** | `/auth` | JWT-based authentication with cookie storage and implicit token refresh |
| **job_tracker** | `/services/jobs` | Full CRUD for job applications with Kanban-style status pipeline and analytics |
| **smart_tasks** | `/services/tasks` | Task management with priorities, categories, due dates, and recurring tasks |
| **football_tracking** | `/services/football` | Proxy layer to external Football Tracking API with background change detection |
| **daily_brief** | `/api/brief` | Aggregated dashboard: today's tasks, job follow-ups, streaks, statistics |
| **platform_registry** | `/services/platforms` | Service registry with health checks and metadata |
| **webhooks** | `/webhooks` | Incoming webhook handler with WebSocket broadcast |
| **websocket** | `/ws` | Real-time connection manager: notifications, presence, activity tracking |
| **sample_platform** | `/services/sample` | Plug-and-play template for adding new services |

---

## API Reference

### Authentication (`/auth`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/auth/login` | Authenticate with email/password, receive JWT cookies | No |
| POST | `/auth/logout` | Clear authentication cookies | Yes |
| POST | `/auth/refresh-token` | Exchange refresh token for new access token | Refresh |
| PUT | `/auth/change-password` | Update password | Yes |

### Job Tracker (`/services/jobs`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/services/jobs` | List jobs (filter by status, search, pagination) | Yes |
| POST | `/services/jobs` | Create job application | Yes |
| GET | `/services/jobs/stats` | Analytics: counts by status, salary ranges, timeline | Yes |
| GET | `/services/jobs/{id}` | Get single job | Yes |
| PUT | `/services/jobs/{id}` | Update job details | Yes |
| PATCH | `/services/jobs/{id}/status` | Update status only (Kanban drag) | Yes |
| DELETE | `/services/jobs/{id}` | Soft delete (archive) | Yes |

**Job Status Pipeline:** `WISHLIST` → `APPLIED` → `PHONE_SCREEN` → `INTERVIEW` → `OFFER` / `REJECTED`

### Smart Tasks (`/services/tasks`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/services/tasks` | List tasks (filter by priority, category, completion) | Yes |
| POST | `/services/tasks` | Create task | Yes |
| GET | `/services/tasks/today` | Tasks due today | Yes |
| GET | `/services/tasks/categories` | User's unique categories | Yes |
| GET | `/services/tasks/{id}` | Get single task | Yes |
| PUT | `/services/tasks/{id}` | Update task | Yes |
| PATCH | `/services/tasks/{id}/complete` | Toggle completion | Yes |
| DELETE | `/services/tasks/{id}` | Soft delete | Yes |

**Priority Levels:** `LOW` | `MEDIUM` | `HIGH` | `URGENT`
**Recurring Types:** `DAILY` | `WEEKLY` | `MONTHLY`

### Football Tracking (`/services/football`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/services/football/stats` | Aggregated counts (users, players, teams, matches, etc.) | Yes |
| GET | `/services/football/users` | List users (search, pagination) | Yes |
| GET | `/services/football/players` | List players (team filter) | Yes |
| GET | `/services/football/players/{id}/avatar` | Player avatar image | Yes |
| GET | `/services/football/teams` | List teams (search) | Yes |
| GET | `/services/football/teams/{id}/logo` | Team logo image | Yes |
| GET | `/services/football/matches` | List matches | Yes |
| GET | `/services/football/goals` | List goals | Yes |
| GET | `/services/football/tournaments` | List tournaments | Yes |
| GET | `/services/football/leagues` | List leagues | Yes |
| GET | `/services/football/rankings` | Rankings | Yes |
| GET | `/services/football/trainings` | Training sessions | Yes |
| GET | `/services/football/attendance` | Attendance records | Yes |
| GET | `/services/football/notifications` | Match notifications | Yes |

### Daily Brief (`/api/brief`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/brief/today` | Today's tasks, job follow-ups, stats, streaks | Yes |

### Platform Registry (`/services/platforms`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/services/platforms` | All registered services with health status | Yes |
| GET | `/services/platforms/{id}/health` | Health check single service | Yes |

### WebSocket (`/ws`)

```
WS /ws?token=<access_token>
```

**Client → Server:**
```json
{"action": "page_change", "page": "football"}
{"action": "ping"}
```

**Server → Client:**
```json
{"type": "notification", "data": {"title": "...", "message": "...", "category": "..."}}
{"type": "presence", "data": {"onlineUsers": [...], "count": 3}}
{"type": "activity", "data": {"userName": "...", "action": "...", "page": "..."}}
```

### Webhooks (`/webhooks`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/webhooks/football` | Receive Football events (validated via `X-Webhook-Secret`) | Secret |

**Supported Events:** `player.created`, `team.created`, `match.created`, `goal.scored`, `card.issued`

### Health

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/health` | Service health check | No |

---

## Authentication

Custom JWT implementation with dual token strategy:

```
                    ┌──────────────┐
                    │  POST /login │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ Validate     │
                    │ credentials  │
                    └──────┬───────┘
                           │
              ┌────────────▼────────────┐
              │  Set httpOnly cookies   │
              │  - access_token (8h)    │
              │  - refresh_token (8h)   │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  Subsequent requests    │
              │  Cookies sent auto      │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  < 1 min to expiry?     │──── No ──→ proceed
              │  Auto-refresh silently  │
              └─────────────────────────┘
```

**Security features:**
- `httpOnly` cookies (no JS access)
- `secure` flag in production (HTTPS only)
- `samesite=none` for cross-origin support
- Optional CSRF double-submit protection
- Header fallback for WebSocket connections
- Implicit token refresh within 1 minute of expiry

**JWT Claims:**
```json
{
  "userId": 1,
  "role": "ADMIN",
  "userName": "Admin",
  "type": "access",
  "fresh": true,
  "iat": 1711000000,
  "exp": 1711028800,
  "jti": "unique-token-id"
}
```

---

## Real-time Features

### WebSocket Connection Manager
- **Per-user tracking:** One active connection per user (latest connection wins)
- **Presence broadcasting:** Online user list updated on connect/disconnect
- **Page tracking:** Users broadcast which page they're viewing
- **Thread-safe:** `asyncio.Lock` for concurrent access safety

### Football Change Detector
- Background async task polling the external Football API every 300 seconds
- Compares entity counts against cached values
- Broadcasts WebSocket notifications when changes are detected (new players, matches, goals, etc.)
- Graceful shutdown on application exit

### Webhook-to-WebSocket Bridge
- Receives structured events via HTTP webhook
- Validates `X-Webhook-Secret` header
- Maps events to UI-friendly notifications (title, message, icon, color)
- Broadcasts to all connected WebSocket clients

---

## Service Registry

Extensible platform registration with health monitoring:

```python
# Each platform registers at startup
registry.register(PlatformService(
    id="football",
    name="Football Tracking",
    description="Match tracking & team analytics",
    prefix="/services/football",
    icon="SportsSoccer",
    color="#10B981",
    health_check_url="https://footballtracking.duckdns.org/dashboard/health"
))
```

**Adding a new platform:**
1. Copy `src/modules/sample_platform/` to `src/modules/your_platform/`
2. Update the router prefix and implement your endpoints
3. Register the service in `run_api.py` lifespan
4. The frontend automatically discovers it via `/services/platforms`

---

## Database Models

### Entity Relationship

```
UserModel (Single Table Inheritance)
├── id (PK), name, email, _password (hashed), role, isDeleted, isAvailable
└── AdminModel (polymorphic on role=ADMIN)

JobApplicationModel
├── id (PK), user_id (FK → users)
├── company, role, link, notes
├── salary_min, salary_max, salary_currency
├── status (WISHLIST | APPLIED | PHONE_SCREEN | INTERVIEW | OFFER | REJECTED)
├── applied_date, follow_up_date
└── is_archived, created_at, updated_at

TaskModel
├── id (PK), user_id (FK → users)
├── title, description, category
├── priority (LOW | MEDIUM | HIGH | URGENT)
├── due_date, is_completed, completed_at
├── recurring_type (DAILY | WEEKLY | MONTHLY)
├── recurring_parent_id (FK → self)
└── is_deleted, created_at, updated_at
```

All models extend `SqlBaseModel` with automatic timestamps and a `update()` method for hydrating from Pydantic schemas.

---

## Getting Started

### Prerequisites
- Python 3.12+
- PostgreSQL (or SQLite for local development)

### Installation

```bash
git clone <repository-url>
cd fusionboard-be
pip install -r requirements.txt
```

### Configuration

Create a `.env` file (see [Environment Variables](#environment-variables)):

```env
APP_ENV=local
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/fusionboard
AUTHJWT_SECRET_KEY=your-secret-key-min-64-chars
ALLOWED_ORIGINS=http://localhost:3000
```

### Run

```bash
# Run migrations
python -m services.run_migration

# Start server
uvicorn services.run_api:api --host 0.0.0.0 --port 8000 --reload
```

The API is available at `http://localhost:8000`. Health check: `GET /health`.

### Default Admin
On first startup, an admin user is automatically created:
```
Email:    admin@fusionboard.io
Password: FusionAdmin2026!
```

---

## Deployment

### Docker

```bash
cd deploy
cp .env.example .env  # Configure environment
docker-compose up --build
```

**Services started:**
1. **Caddy** — Reverse proxy with automatic HTTPS (ports 80/443)
2. **API** — FastAPI application (port 8000, internal)

**Startup sequence:**
1. Alembic migrations run automatically
2. Database tables created if missing
3. Default admin user seeded
4. Platform services registered
5. Football change detector starts in background

### Docker Compose Architecture

```
┌─────────┐     ┌───────────────────────┐
│  Caddy   │────▶│   FastAPI (uvicorn)   │
│  :80/443 │     │       :8000           │
└─────────┘     └───────────┬───────────┘
                            │
                  ┌─────────▼─────────┐
                  │   PostgreSQL      │
                  │   (external/cloud)│
                  └───────────────────┘
```

---

## Environment Variables

### Core
| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `production` | `local` or `production` — affects cookie security, DB defaults |
| `DATABASE_URL` | — | Full PostgreSQL connection string |
| `PORT` | `8000` | Server port |
| `ALLOWED_ORIGINS` | `*` | Comma-separated CORS origins |

### JWT & Authentication
| Variable | Default | Description |
|----------|---------|-------------|
| `AUTHJWT_SECRET_KEY` | — | **Required.** Secret for signing JWTs (64+ chars recommended) |
| `AUTHJWT_TOKEN_LOCATION` | `cookies` | Token location: `cookies`, `headers`, or both |
| `AUTHJWT_COOKIE_SAMESITE` | auto | `lax`, `strict`, or `none` (auto-set by APP_ENV) |
| `AUTHJWT_COOKIE_SECURE` | auto | `true` in production, `false` in local |
| `AUTHJWT_COOKIE_DOMAIN` | — | Optional cookie domain |
| `AUTHJWT_COOKIE_CSRF_PROTECT` | `false` | Enable CSRF double-submit cookies |

### External Services
| Variable | Default | Description |
|----------|---------|-------------|
| `FOOTBALL_TRACKING_API_URL` | — | Football Tracking API base URL |
| `FOOTBALL_TRACKING_API_KEY` | — | API key for Football service |
| `FOOTBALL_TRACKING_API_TIMEOUT` | `30` | Request timeout in seconds |
| `FUSIONBOARD_WEBHOOK_SECRET` | — | Shared secret for webhook validation |

---

## Tech Stack

| Category | Technology |
|----------|-----------|
| Framework | FastAPI 0.115 |
| Language | Python 3.12 |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic 1.14 |
| Database | PostgreSQL (psycopg2) |
| Auth | PyJWT 2.10 |
| Validation | Pydantic 2.10 |
| Server | Uvicorn 0.34 |
| Reverse Proxy | Caddy 2 |
| Containerization | Docker |
