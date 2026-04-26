# Server — Backend (Python, Clean Architecture)

Deterministic engine of rules + (planned) FastAPI app. Web frontend will live under `web/` once scaffolded.

## Setup

```bash
cd server
pip install -e ".[dev]"
```

## Quality gate

```bash
pytest                       # unit tests
ruff check src tests         # linter
mypy src                     # strict type check
```

Or just run the slash command `/test` in Claude Code.

## Run the bot-vs-bot simulator

```bash
agora-sim                    # 1 match with seed 42
agora-sim --seed 7           # specific seed (deterministic)
agora-sim --runs 100         # 100 matches, prints win rates
agora-sim --quiet            # final result only
```

## Layered structure (Clean Architecture)

```
src/agora/
├── domain/                  Pure entities and value objects (no I/O)
│   ├── enums.py             Essence, Archetype, SkillKind, TargetKind, EffectKind
│   ├── character.py         Character, Skill, Effect (immutable definitions)
│   ├── match.py             MatchState, PlayerState, CharacterState, Action
│   ├── arena.py             Arena, ArenaModifier
│   ├── draft.py             DraftState, DraftPhase
│   └── events.py            Event log entries
├── application/
│   ├── ports.py             CharacterRepository, ArenaRepository, RandomSource
│   ├── engine/              Object-oriented match engine
│   │   ├── match_engine.py        MatchEngine orchestrator class
│   │   ├── effect_handlers.py     EffectHandler hierarchy (Damage, Heal, ...)
│   │   ├── status_ticks.py        StatusTickHandler hierarchy (Poison, Bleed, Regen)
│   │   ├── arena_strategies.py    ArenaModifierStrategy hierarchy
│   │   ├── skill_validator.py     Cooldown / cost / status restrictions
│   │   └── status_predicates.py   Pure predicates over CharacterState statuses
│   └── use_cases/           Thin facades over the engine + draft service
│       ├── start_match.py
│       ├── resolve_turn.py
│       ├── apply_arena.py
│       └── draft.py         DraftService (start/ban/pick/finalize/cancel)
├── infrastructure/
│   ├── yaml_repository.py
│   ├── yaml_arena_repository.py
│   ├── in_memory_draft_repository.py     swap for Redis in production
│   └── seeded_random.py
└── interfaces/
    ├── cli.py                            bot-vs-bot simulator
    └── api/                              FastAPI app
        ├── main.py                       app factory + uvicorn entrypoint
        ├── settings.py                   pydantic-settings (env vars)
        ├── security.py                   JWT helpers + current_user dep
        ├── oauth.py                      Authlib provider registry
        ├── match_runtime.py              in-process match store + dispatcher
        └── routers/                      health, characters, arenas, auth, match
```

**Dependency rule:** outer layers may import inner ones; never the reverse. If you need infrastructure inside a use case, define a Protocol in `application/ports.py` and inject it.

### How the engine dispatches

`MatchEngine.resolve_turn` walks each action and looks up handlers from the registries:

```python
EFFECT_HANDLERS: dict[EffectKind, EffectHandler]      # one entry per EffectKind
STATUS_TICK_HANDLERS: dict[str, StatusTickHandler]    # poison, bleed, regen, ...
STRATEGY_REGISTRY: dict[str, ArenaModifierStrategy]   # one entry per arena modifier kind
```

Adding a new effect / tick / arena modifier is a subclass + registry entry. The orchestrator's dispatch loop never changes.

## Current status

- 16 playable characters across 10 mythologies (full MVP roster).
- 3 arenas (`neutral`, `olympus`, `underworld`) with two modifier kinds wired
  into the engine (`hp_boost_by_mythology`, `apply_status_at_start`).
- Engine: damage, healing, cooldowns, costs, side alternation, seeded RNG,
  win condition, arena hooks.
- Statuses: poison, bleed, regen (DoT/HoT); stun, silence, disarm,
  invulnerable, vulnerable, marked, damage_reduction, damage_buff,
  destructible_shield; piercing and `true` modifiers.
- FastAPI app: `/health`, `/characters`, `/arenas`, `/auth/*`, `/match/*`
  (REST + WebSocket).
- OAuth 2.0: Google end-to-end via Authlib (gated by env credentials),
  Apple route still 501.
- Draft service (start/ban/pick/finalize) with in-memory repository and
  full state-machine tests.
- 48 tests passing.

## Next steps

- Remaining statuses: drained tick (essence drip per turn), reflective,
  copy effects.
- Apple OAuth wiring (form-encoded POST callback, .p8 client secret JWT).
- Redis-backed drafts and matchmaking.
- Persistence: PostgreSQL for players, matches, missions; Alembic migrations.
- Full battle UI on the frontend (action queue, target selection, animations).
