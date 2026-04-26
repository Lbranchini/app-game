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
│   └── events.py            Event log entries
├── application/             Orchestration layer (depends on domain only)
│   ├── ports.py             CharacterRepository, RandomSource (Protocols)
│   └── use_cases/
│       ├── start_match.py
│       └── resolve_turn.py
├── infrastructure/          Adapter implementations
│   ├── yaml_repository.py   loads YAMLs from data/characters/
│   └── seeded_random.py     deterministic RNG
└── interfaces/              Entry points
    └── cli.py               bot-vs-bot simulator (FastAPI added later)
```

**Dependency rule:** outer layers may import inner ones; never the reverse. If you need infrastructure inside a use case, define a Protocol in `application/ports.py` and inject it.

## Current status (vertical slice)

- 3 playable characters: Achilles, Athena, Anubis (cover physical damage, support, DoT)
- 15 tests passing
- Engine: damage, healing, cooldowns, costs, side alternation, seeded RNG, win condition
- Statuses implemented: poison (DoT), damage_reduction, destructible_shield, damage_buff, invulnerable, piercing
- CLI bot-vs-bot runs full matches end-to-end

## Next steps (out of this slice)

- 13 remaining MVP characters
- Statuses to implement: stun, silence, disarm, drained, bleed (proportional version), regen, marked, vulnerable, reflective, copy
- More effect kinds: copy, reflect, counter
- FastAPI app on top of the engine
- Persistence (PostgreSQL + Redis)
