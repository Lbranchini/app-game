---
description: Scaffold a new playable character (YAML + tests)
argument-hint: "<character-id> [mythology]"
---

Add a new character to the roster. The user provides at minimum a character id (e.g. `medusa`).

Steps:

1. Confirm with the user: full name, mythology folder (`greek`, `norse`, `egyptian`, ...), archetype (one of `damage_dealer`, `healer`, `tank`, `stunner`, `drainer`, `trickster`, `support`, `leader`), and HP base.
2. Read `data/characters/greek/achilles.yaml` to recall the schema.
3. Create `data/characters/<mythology>/<id>.yaml` with 3 skills (basic, secondary, ultimate). Use existing effect kinds from `server/src/agora/domain/enums.py` only — do NOT invent new ones without coordinating an engine change.
4. Add at least one test in `server/tests/` exercising the new character's signature mechanic.
5. Run `pytest` and `agora-sim --runs 50 --quiet` to confirm nothing broke.
6. Update `docs/05-characters.md` with the new character entry.

If the proposed kit needs a status effect or effect kind that does not yet exist in the engine, STOP and surface that to the user before writing any YAML — adding new kinds is an engine change, not a data change.
