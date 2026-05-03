# 04 — Roadmap

> Estimates assume one part-time developer. Scale up or down for the actual team.

---

## Phase 0 — Pre-production (2–3 weeks)

**Goal:** validate the concept before writing application code.

- [x] Sign off on this planning bundle.
- [ ] Resolve remaining architecture decisions (hosting, i18n).
- [ ] Cartoon mood board: palette, outline weight, animation style (references: Hades 2D, Slay the Spire, Cult of the Lamb).
- [ ] Paper-prototype a full match: print 6 character cards with skills and play yourself. Find rule holes before coding.
- [x] Repository setup: CI baseline, linter, formatter, PR rules.

**Deliverable:** consolidated GDD (this `/docs` set) + a playable paper prototype.

---

## Phase 1 — Engine of rules (4–6 weeks)

**Goal:** authoritative Python engine that resolves matches via API, no UI.

- [x] FastAPI + uv + ruff + mypy + pytest project scaffold (in `server/`).
- [x] YAML schema + Pydantic v2 validation.
- [x] Repository loader.
- [x] Engine of turns (pure module): match state, action queue, resolution, cooldowns, statuses.
- [x] CLI bot-vs-bot simulator.
- [x] All 16 character YAMLs.
- [x] Status effects: poison, bleed, regen, drained, stun, silence, disarm, marked, vulnerable, invulnerable, damage_reduction, damage_buff, destructible_shield, reflective, **stealth** (un-targetable, broken on attack — wired into Mulan + Sun Wukong).
- [ ] `copy` (Loki's third archetype lever): blocked on plumbing for granted-skill tracking on `CharacterState` + `SkillValidator`. Effect handler intentionally omitted until that lands — see comment in `effect_handlers.py`.
- [x] Test coverage ≥ 80%. (Currently **89%** — measured via `pytest --cov=agora`.)

**Deliverable:** `pytest` green with ≥ 80% coverage. CLI runs an end-to-end match in < 1s. ✓

---

## Phase 2 — Web client, local-only (4–6 weeks)

**Goal:** browser UI playing one match against a local AI through a single FastAPI process.

- [x] React + TypeScript + Vite + Tailwind scaffold in `web/`.
- [x] Home screen, team-select, battle, character collection.
- [x] Battle UI: essence HUD, character panel, skill panel, action queue, READY button.
- [x] Placeholder animations: attack (shake + floating numbers), damage, heal, VS splash, essence pop, hit/heal SFX. (See `web/src/pages/Battle.tsx`.)
- [ ] Local AI: random valid action. (Bot exists in CLI sim; not yet exposed in the browser UI.)

**Deliverable:** local dev environment where the same engine drives the browser UI in a complete 3v3 match. ✓

---

## Phase 3 — Multiplayer + accounts (4–6 weeks)

**Goal:** functional PvP.

- [x] **OAuth 2.0 sign-in** with Google. Apple stub returns 501 — see `routers/auth.py:apple_callback` for the implementation steps.
- [x] Matchmaking (Elo-based queue).
- [x] WebSocket client ↔ server (with per-IP rate limiting on auth + dev endpoints).
- [x] Authoritative state sync.
- [x] Disconnect handling — 30s reconnect grace + server-side forfeit, application-layer heartbeat (15s) catches half-open sockets, client auto-reconnects with exponential backoff (1/2/4/8/16s, 6 attempts) and shows an overlay.
- [x] Server-enforced **turn deadline** (60s) with auto-resolve; client mirrors the deadline for the countdown.
- [ ] Basic telemetry (match length, actions per turn, drop rate). Some counters live (mission service, ELO deltas); structured logging + metrics endpoint still to do.
- [x] **Mission system** (see `docs/09-missions.md`): per-player progress counters, MissionService after each match, "Characters" UI with progress bars.
- [x] **Ranked draft (ban-pick)** — see `docs/10-draft.md`. Pre-match phase running in-memory with WebSocket-driven UI.
- [x] **Arenas** — see `docs/11-arenas.md`. Server picks an arena before draft; modifiers apply at match start (and selected hooks during the match).
- [x] **Local stack**: `docker compose up` orchestrates server + web + optional Postgres (`--profile postgres`); SQLite is the default.
- [x] **Alembic migrations**: `0001_initial` baseline; production deploys run `alembic upgrade head`.
- [x] **CI**: `.github/workflows/ci.yml` runs ruff + mypy --strict + pytest (with coverage XML) + Alembic up/down smoke + tsc + vitest on every PR.

**Deliverable:** closed beta with ~20 friends running real matches. ✓ (infrastructure-ready)

---

## Phase 4 — Content + polish (6–8 weeks)

- [ ] Roster from 16 → 20 characters (4 new, covering under-represented mythologies).
- [ ] Balance: 3 playtest rounds, adjustments via PR.
- [ ] Real animations (artist or asset pack).
- [ ] Audio: ambient music + per-skill SFX.
- [ ] VFX (particles).
- [ ] Profile / progression screen.
- [ ] Localization: PT-BR + EN.

**Deliverable:** v0.9, soft-launch quality.

---

## Phase 5 — Web launch (4 weeks)

- [ ] Public web hosting (TLS, custom domain).
- [ ] Privacy policy + terms.
- [ ] LGPD/GDPR compliance.
- [ ] Landing page.
- [ ] Initial marketing plan (Reddit, TikTok, mythology/tactics Discords).

**Deliverable:** v1.0 live on the web.

---

## Phase 6 — Native mobile (post-v1.0)

The web architecture (server-authoritative, REST + WS) is mobile-ready. Two options:

- **React Native** (or Capacitor) — reuse most of the React/TS code; ship Android + iOS from one codebase.
- **A separate native client** (e.g. Godot or SwiftUI/Jetpack Compose) — heavier investment, better feel.

Decision deferred to after web traction.

---

## Continuous post-launch

- Monthly balance patches.
- One new character every two weeks.
- Seasonal events (Halloween → Celtic; Carnival → Orixás; ...).
- Quarterly Battle Pass.

---

## Explicit non-goals for the MVP

Cut deliberately. Do **not** ship before v1.0:

- Guild / clan systems.
- In-game chat.
- Replays.
- Spectator mode.
- Cosmetics catalog.
- PvE / campaign.
- Voice acting.
- Native mobile clients.

**Rule of thumb:** small scope ships. Large scope doesn't.
