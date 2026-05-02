# 04 — Roadmap

> Estimates assume one part-time developer. Scale up or down for the actual team.

---

## Phase 0 — Pre-production (2–3 weeks)

**Goal:** validate the concept before writing application code.

- [ ] Sign off on this planning bundle.
- [ ] Resolve remaining architecture decisions (hosting, i18n).
- [ ] Cartoon mood board: palette, outline weight, animation style (references: Hades 2D, Slay the Spire, Cult of the Lamb).
- [ ] Paper-prototype a full match: print 6 character cards with skills and play yourself. Find rule holes before coding.
- [ ] Repository setup: CI baseline, linter, formatter, PR rules.

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
- [x] Status effects: poison, bleed, regen, drained, stun, silence, disarm, marked, vulnerable, invulnerable, damage_reduction, damage_buff, destructible_shield, reflective.
- [ ] `copy` (Loki's third archetype lever): blocked on plumbing for granted-skill tracking on `CharacterState` + `SkillValidator`. Effect handler intentionally omitted until that lands — see comment in `effect_handlers.py`.
- [ ] Test coverage ≥ 80%.

**Deliverable:** `pytest` green with ≥ 80% coverage. CLI runs an end-to-end match in < 1s.

---

## Phase 2 — Web client, local-only (4–6 weeks)

**Goal:** browser UI playing one match against a local AI through a single FastAPI process.

- [ ] React + TypeScript + Vite + Tailwind scaffold in `web/`.
- [ ] Home screen, team-select, battle, character collection.
- [ ] Battle UI: essence HUD, character panel, skill panel, action queue, READY button.
- [ ] Placeholder animations: attack, damage, heal, status pulse.
- [ ] Local AI: random valid action.

**Deliverable:** local dev environment where the same engine drives the browser UI in a complete 3v3 match.

---

## Phase 3 — Multiplayer + accounts (4–6 weeks)

**Goal:** functional PvP.

- [ ] **OAuth 2.0 sign-in** with Google and Apple (see `docs/03-architecture.md` §9).
- [ ] Matchmaking (Elo-based queue).
- [ ] WebSocket client ↔ server.
- [ ] Authoritative state sync.
- [ ] Disconnect handling (60s timeout → loss).
- [ ] Basic telemetry (match length, actions per turn, drop rate).
- [ ] **Mission system** (see `docs/09-missions.md`): per-player progress counters, MissionService after each match, "Characters" UI with progress bars.
- [ ] **Ranked draft (ban-pick)** — see `docs/10-draft.md`. Pre-match phase running in Redis with WebSocket-driven UI.
- [ ] **Arenas** — see `docs/11-arenas.md`. Server picks an arena before draft; modifiers apply at match start (and selected hooks during the match).

**Deliverable:** closed beta with ~20 friends running real matches.

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
