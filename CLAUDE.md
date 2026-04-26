# CLAUDE.md

Project-wide instructions for Claude Code working on this repository.

## Project

Web game (mobile coming later) — turn-based 3v3 tactical battler with characters drawn from world mythology and history. All public-domain figures; no derivative IP.

## Tech stack

- **Backend:** Python 3.11+, FastAPI (planned), Pydantic v2, SQLAlchemy + PostgreSQL + Redis (planned). Engine of rules is a pure module under Clean Architecture (see below).
- **Frontend:** React 18 + TypeScript + Vite + Tailwind (web first; native mobile is a later phase).
- **Game data:** YAML files under `data/characters/`, validated by Pydantic.

## Repository layout

```
app-game/
├── .claude/                  Claude Code config + slash commands + agents
├── data/characters/          YAML character definitions (greek/, egyptian/, ...)
├── docs/                     Game design + architecture documentation
├── server/                   Python backend (Clean Architecture)
│   └── src/agora/
│       ├── domain/           Pure entities, enums, value objects (no I/O)
│       ├── application/      Use cases + ports (interfaces for adapters)
│       ├── infrastructure/   Adapter implementations (YAML loader, RNG, DB)
│       └── interfaces/       Entry points (CLI now; FastAPI later)
└── web/                      React frontend (planned, not scaffolded yet)
```

## Architecture rules (Clean Architecture)

Dependency direction: **outer → inner only**. Inner layers must not import outer ones.

| Layer | May import from |
|---|---|
| `domain` | (only stdlib + pydantic) |
| `application` | `domain` |
| `infrastructure` | `domain`, `application` |
| `interfaces` | `domain`, `application`, `infrastructure` |

If you find yourself adding `from agora.infrastructure...` inside `domain/` or `application/`, stop — that's a violation. Define a Protocol in `application/ports.py` instead and inject the implementation.

## Language

All code, identifiers, comments, and documentation are in **English**. Character names use their canonical English spelling (Achilles, Athena, Anubis, Sun Wukong). Skill names are translated.

## Coding rules (server)

- Type hints are required. `mypy --strict` must pass.
- Format/lint with `ruff` (config in `pyproject.toml`).
- Use Pydantic v2 models for all data crossing layer boundaries.
- Default to no comments. Only write a comment when the *why* is non-obvious.
- Tests are pytest. Each new effect kind, status type, or use case needs a test.

## Workflows

- `/test` — run pytest + ruff + mypy.
- `/sim` — run the bot-vs-bot simulator (good signal on balance after data changes).
- `/add-character` — guided workflow to add a new character.

## Common pitfalls

- Don't put game rules in the loader. The loader returns plain entities; rules live in `application/use_cases/`.
- Don't reference Naruto Arena or any commercial property by name in code, comments, or commit messages — mechanics are fine, but staying clean of references avoids ambiguity.
- Don't add new `EffectKind` or status names without also adding the engine handler — Pydantic will accept the YAML, but the engine will silently ignore it.

## Sources of truth

- Game mechanics: `docs/02-mechanics.md`
- Architecture: `docs/03-architecture.md`
- Roster + skill specs: `docs/05-characters.md`
- Balance philosophy: `docs/06-balance.md`
- Glossary: `docs/07-glossary.md`
- Missions / progression: `docs/09-missions.md`
