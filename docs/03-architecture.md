# 03 — Technical Architecture

> **Locked decisions (Apr 2026):**
> - First platform: **Web** (browser). Native mobile is a later phase.
> - Frontend: **React 18 + TypeScript + Vite + Tailwind CSS**
> - Backend: **Python 3.11+ with FastAPI**, structured as **Clean Architecture**
> - Persistence: **PostgreSQL 16 + Redis**
> - Art: **2D cartoon**
> - MVP roster: **16 characters**

---

## 1. Why web first

A turn-based card-style game maps cleanly onto HTML/CSS/Canvas — no demanding 3D rendering, no controller input. Web buys us:

- **Fastest iteration loop** — no app store review for every change.
- **Frictionless onboarding** — share a URL, opponent is in a match in seconds.
- **Cross-device by default** — desktop browsers, mobile browsers, tablets.
- **A solid base for native mobile** — all game logic and state lives on the server, so the eventual React Native (or Capacitor) wrapper just renders the same protocol.

Mobile is deferred to a later phase, not abandoned. The architecture below preserves that path.

---

## 2. Frontend stack (web)

| Layer | Choice | Why |
|---|---|---|
| Framework | **React 18** | Most popular, broad community, vast component ecosystem |
| Language | **TypeScript 5** | Strongly typed contract with the server |
| Build | **Vite** | Sub-second hot reload, modern ESM, lean output |
| Styling | **Tailwind CSS** | Fast UI iteration without bespoke CSS files |
| State (client) | **Zustand** | Tiny, ergonomic, no boilerplate |
| State (server) | **TanStack Query** | Caching, refetching, optimistic updates for REST endpoints |
| WebSocket client | Native `WebSocket` + a thin wrapper | Match channel uses WSS |
| Animation | **Framer Motion** | Declarative animations for cards and skill effects |
| Routing | **TanStack Router** or **React Router** | TBD |
| Testing | **Vitest** + **React Testing Library** | Aligned with Vite |
| Linting | **ESLint + Prettier** + **TypeScript strict** | Standard |

### Folder layout (planned `web/`)

```
web/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── api/                    REST + WebSocket clients
│   ├── pages/
│   │   ├── home.tsx
│   │   ├── team-select.tsx
│   │   ├── battle.tsx
│   │   └── characters.tsx       (mission progress)
│   ├── components/
│   │   ├── battle/
│   │   ├── character/
│   │   └── ui/
│   ├── stores/                 zustand stores
│   ├── hooks/
│   └── types/                   shared TS types (mirrors backend Pydantic)
└── public/
```

---

## 3. Backend stack (Python + FastAPI)

### Why Python over Node/Go

- Clean, expressive language for rule-heavy logic (status effects, priority, modifiers).
- `pydantic` validates payloads and YAML data files in one place.
- `pytest` is excellent for the hundreds of skill-interaction tests this game will need.
- FastAPI is async-first, has native WebSockets, and auto-generates OpenAPI for the frontend.
- Performance is not a concern — turn-based math resolves in milliseconds.

### Components

| Component | Tool | Purpose |
|---|---|---|
| HTTP/WebSocket | **FastAPI** | Async API + WS |
| Schema validation | **Pydantic v2** | YAML/JSON of characters, request/response DTOs |
| DB driver / ORM | **SQLAlchemy 2.0** + **Alembic** | Postgres |
| Cache + matchmaking | **Redis** | Queues, Elo lookups, sessions |
| Background jobs | **arq** | Post-match rewards, cleanup |
| Auth | **Firebase Auth** verified server-side | Google + Apple sign-in |
| Tests | **pytest** + **hypothesis** | Property-based tests on the engine |
| Lint / types | **ruff + mypy** | Strict |
| Hosting | **Fly.io** or **Railway** | Easy deploy, decent autoscale |
| Container | **Docker** | Reproducible runtime |

---

## 4. Clean Architecture in the backend

```
server/src/agora/
├── domain/             pure entities, enums, value objects
├── application/        use cases + ports (Protocols)
├── infrastructure/     adapter implementations (YAML, DB, Redis, RNG)
└── interfaces/         entry points (CLI now; FastAPI app next)
```

**Dependency rule:** outer layers import from inner layers, never the reverse.

| Layer | May import from |
|---|---|
| `domain` | stdlib + pydantic only |
| `application` | `domain` |
| `infrastructure` | `domain`, `application` |
| `interfaces` | `domain`, `application`, `infrastructure` |

### Why this matters here

- **The engine** (the most valuable code) sits in `domain` + `application`. It has zero I/O. It can run in a unit test, a CLI, an HTTP request handler, or a batch balance simulator without changes.
- **Adapters** (YAML loader, RNG, future DB repository, future FastAPI handlers) plug into `application/ports.py`. To swap PostgreSQL for SQLite in tests, write another adapter — the use cases never know.
- **Future mobile**: when we build the React Native client, we reuse the exact same FastAPI endpoints. No engine duplication.

### Engine signature

```python
def resolve_turn(
    state: MatchState,
    actions: list[Action],
    repository: CharacterRepository,    # port
    rng: RandomSource,                  # port
) -> tuple[MatchState, list[Event]]: ...
```

Pure function: same inputs → same outputs. Replays are free.

---

## 5. System diagram

```
Web (React)
    │
    │ HTTPS (REST)  ── auth, profile, matchmaking, missions
    │ WSS  ──────── live match channel
    ↓
┌──────────────────────────────────────────────┐
│ FastAPI app (interfaces/api)                 │
│  /auth, /profile, /matchmaking, /ws/match    │
│        │                                     │
│        ↓                                     │
│  Use cases (application)                     │
│        │                                     │
│        ↓                                     │
│  Domain entities + engine                    │
└──────────────────────────────────────────────┘
        │             │              │
        ↓             ↓              ↓
   PostgreSQL      Redis        YAML files
   (durable)       (transient)  (data/characters/)
```

---

## 6. Data schema sketch (PostgreSQL)

```sql
CREATE TABLE players (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  firebase_uid TEXT UNIQUE NOT NULL,
  username TEXT UNIQUE NOT NULL,
  elo INT NOT NULL DEFAULT 1000,
  unlocked_characters JSONB NOT NULL
    DEFAULT '["achilles","athena","thor","anubis","isis","anansi","joan","loki"]',
  progress JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen TIMESTAMPTZ
);

CREATE TABLE matches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  player_a UUID NOT NULL REFERENCES players(id),
  player_b UUID NOT NULL REFERENCES players(id),
  team_a JSONB NOT NULL,
  team_b JSONB NOT NULL,
  state JSONB NOT NULL,
  current_turn INT NOT NULL DEFAULT 0,
  current_player UUID REFERENCES players(id),
  winner UUID REFERENCES players(id),
  rng_seed BIGINT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ended_at TIMESTAMPTZ
);

CREATE INDEX idx_matches_active ON matches(current_player) WHERE ended_at IS NULL;

CREATE TABLE match_actions (
  match_id UUID NOT NULL REFERENCES matches(id),
  turn INT NOT NULL,
  player UUID NOT NULL REFERENCES players(id),
  actions JSONB NOT NULL,
  ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (match_id, turn, player)
);
```

Characters do **not** live in the DB — they live in `data/characters/*.yaml`, version controlled. Balance changes are pull requests.

---

## 7. Match lifecycle

```
[Player A]                  [FastAPI Server]              [Player B]
    │                              │                            │
    ├── POST /matchmaking/join ──>│                            │
    │                              │<── POST /matchmaking/join ─┤
    │                              │  (Redis matchmaker pairs)  │
    │                              │                            │
    │<── WS: match_found ──────────┼── WS: match_found ────────>│
    │                              │                            │
    ├── WS: actions(turn=1) ──────>│                            │
    │                              │ resolve_turn(...)          │
    │<── WS: state(turn=1) ────────┼── WS: state(turn=1) ──────>│
    │                              │                            │
    │                              │<── WS: actions(turn=2) ────┤
    │<── WS: state(turn=2) ────────┼── WS: state(turn=2) ──────>│
    │             ...                                           │
```

---

## 8. Anti-cheat

- The server is the **only source of truth**. Clients render and predict, never decide.
- Every action is validated server-side: alive? cooldown clear? enough essence? valid target? not stunned/silenced?
- Invalid action → ignored + `state_correction` pushed to client.
- RNG is server-seeded. Clients cannot fabricate random outcomes.

---

## 9. Open decisions

- [ ] Hosting: Fly.io (cheaper) or GCP Cloud Run (more scalable)?
- [ ] Balance dashboard: Streamlit app or raw SQL queries against PG?
- [ ] i18n: keys per language inside YAMLs, or `.po` files?
