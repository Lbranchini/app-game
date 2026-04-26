# Agora of Myths (working title)

Web-first turn-based 3v3 tactical battler with characters drawn from world mythology and history (Greek, Norse, Egyptian, Japanese, Aztec, African, Mesopotamian, British, and more).

## One-line pitch

> Chess with superpowers: build a team of three legends, manage energy and cooldowns, and duel other players in 8–12 minute matches.

## Locked decisions

| Item | Decision |
|---|---|
| First platform | **Web** (browser). Native mobile (Android + iOS) is a later phase. |
| Frontend | **React 18 + TypeScript + Vite + Tailwind CSS** |
| Backend | **Python 3.11+ with FastAPI**, structured as **Clean Architecture** (`domain` / `application` / `infrastructure` / `interfaces`) |
| Persistence | PostgreSQL 16 + Redis |
| Art direction | **2D cartoon** (vibrant palette, clean outlines, expressive) |
| MVP roster | **16 characters** spanning 10 mythologies |
| Business model | Free-to-play, monetized through cosmetics and themed expansions (no pay-to-win) |
| MVP scope | Battles + a mission-based progression system to unlock characters |

## Copyright posture

**Game mechanics** (turns, essence costs, cooldowns, 3v3 layout, status effects) are standard tactical-RPG vocabulary and are not protected by copyright — they are reused and referenced freely.

**Characters, names, and skills** are designed from scratch using **public-domain figures** (mythology and ancient history). No kit copies any identifiable character from another protected work — every one of the 16 is an original design occupying a classic genre archetype.

## Documentation

| File | Content |
|---|---|
| [`docs/01-overview.md`](docs/01-overview.md) | Product vision, audience, monetization |
| [`docs/02-mechanics.md`](docs/02-mechanics.md) | Turn system, essences, skill kinds, statuses |
| [`docs/03-architecture.md`](docs/03-architecture.md) | React + FastAPI + Postgres + Redis (Clean Architecture) |
| [`docs/04-roadmap.md`](docs/04-roadmap.md) | Phases from MVP to v1.0 |
| [`docs/05-characters.md`](docs/05-characters.md) | 16-character roster with full kits |
| [`docs/06-balance.md`](docs/06-balance.md) | Balance philosophy, team archetypes |
| [`docs/07-glossary.md`](docs/07-glossary.md) | Game terminology |
| [`docs/09-missions.md`](docs/09-missions.md) | Missions and character unlocks |

## Repository layout

```
.
├── .claude/             Claude Code config (slash commands, agents)
├── data/characters/     YAML data, grouped by mythology
├── docs/                Game design + architecture docs
├── server/              Python backend (Clean Architecture)
└── web/                 React frontend (planned, not scaffolded yet)
```

## Quick start (backend)

```bash
cd server
pip install -e ".[dev]"
pytest                      # 15 tests
agora-sim --runs 100 --quiet
```

## Status

Phase 0 (planning) complete. Phase 1 (engine of rules) has a working **vertical slice**: 3 characters (Achilles / Athena / Anubis) covering damage, support, and DoT. Engine handles damage, healing, cooldowns, costs, alternating turns, seeded RNG, win condition, plus statuses (poison, damage reduction, destructible shield, damage buff, invulnerable, piercing). Bot-vs-bot CLI runs full matches end-to-end.

Next steps: complete the remaining 13 characters, implement missing statuses (stun, silence, drain, etc.), expose the engine via FastAPI, scaffold the React web client.
