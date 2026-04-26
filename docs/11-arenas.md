# 11 — Arenas

> Each match takes place in an **arena** that imposes a global condition for the duration. Arenas are picked by the server before draft (see `docs/10-draft.md`) so that bans and picks can be made with the modifier in mind.

---

## 1. Why arenas

A neutral match floor flattens strategy: everyone always values the same skills the same way. A modifier per match changes the value calculation:

- A healing-leaning arena makes burst comps less dominant.
- A poison-pulse arena rewards healers and tanks.
- A vigor-friendly arena pushes physical-damage picks up the value chain.

Players have to think *"given this arena, what comp covers it?"* before drafting.

---

## 2. Arena anatomy

```yaml
# data/arenas/olympus.yaml
id: olympus
name: Mount Olympus
description: |
  The throne of the Greek gods. Anyone of Greek origin draws additional
  inspiration on this peak.

modifiers:
  - kind: hp_boost_by_mythology
    mythology: Greek
    value: 5
```

```yaml
# data/arenas/underworld.yaml
id: underworld
name: The Underworld
description: |
  Cold mists creep through every chamber. Death lingers in the air.

modifiers:
  - kind: apply_status_at_start
    status: poison
    duration: 3
    value: 5
    target: all
```

---

## 3. Modifier kinds (MVP catalog)

Implement these in order of priority. The engine ignores unknown modifier kinds with a log line — never crashes — so adding a new modifier is purely additive.

| Modifier | Trigger | Behavior |
|---|---|---|
| `hp_boost_by_mythology` | match start | Adds `value` to `base_hp` of any character whose mythology matches `mythology`. |
| `apply_status_at_start` | match start | Applies the named status to `target` (`all`, `side_a`, `side_b`) at turn 1. |
| `essence_bonus_at_start` | match start | Grants `value` extra essences of `essence` to `target` side. |
| `damage_modifier_global` | every damage event | Adjusts damage of class `damage_class` by `value` (positive or negative). |
| `healing_efficiency` | every heal event | Multiplies healed amount by `multiplier` (e.g. 0.75 for "healing 25% less effective"). |
| `cost_surcharge_for_kind` | when paying cost | Adds `+value` generic to skill kind (e.g. `ultimate`). |
| `pulse_damage` | turn N start | Deals `value` piercing damage to `target` every K turns starting on turn `start_turn`. |

For MVP, only `hp_boost_by_mythology` and `apply_status_at_start` are implemented in code — the others are documented and become work items as new arenas land.

---

## 4. Sample arena set (eight)

A balanced rotation of eight arenas covers most of the strategic dimensions. The MVP ships with all eight defined; the engine handles the modifier kinds it knows.

| Arena | Theme | Modifier highlight |
|---|---|---|
| **Mount Olympus** | Greek peak | Greek characters: +5 HP. |
| **The Underworld** | Egyptian / Greco-Roman afterlife | All characters: poison(5) for 3 turns from turn 1. |
| **Library of Alexandria** | Knowledge | Both sides start with +2 Mind essence. |
| **Sacred Battlefield** | Holy ground | Healing 25% less effective. |
| **Volcano** | Forge of Hephaestus / Vulcan | Physical damage +5. |
| **Sanctuary of the Mute** | Silence | Ultimate skills cost +1 generic. |
| **Garden of Eden** | Fertility | All allies regen 5 HP / turn. |
| **Stormy Sea** | Poseidon's domain | Pulse: turn 5+, 10 piercing damage to a random character per side. |

Each arena needs a YAML file in `data/arenas/`. MVP ships **only the first two** with engine support; the rest are designed and waiting.

---

## 5. How arenas plug into the engine

```
start_match(...)
   │
   ├── builds initial MatchState as before
   ├── loads Arena via ArenaRepository
   ├── stores arena_id in MatchState
   └── runs Arena.apply_match_start(state)
         └── walks modifiers; for kinds the engine knows, mutates state

resolve_turn(...)
   │
   ├── Arena.apply_turn_start(state)        ← pulse damage, etc.
   ├── tick statuses
   ├── resolve actions (with arena hooks on damage / heal / cost)
   └── Arena.apply_turn_end(state)
```

The Arena object owns its hook methods so the engine doesn't grow a giant `if arena_id == "olympus"` switch — modifiers live in data.

---

## 6. Domain model

```python
# domain/arena.py
class ArenaModifier(BaseModel):
    kind: str
    mythology: str | None = None
    status: str | None = None
    duration: int = 0
    value: int = 0
    multiplier: float = 1.0
    essence: Essence | None = None
    target: Literal["all", "side_a", "side_b"] = "all"
    damage_class: DamageClass | None = None
    skill_kind: SkillKind | None = None
    start_turn: int = 1
    every: int = 1

class Arena(BaseModel):
    id: str
    name: str
    description: str
    modifiers: list[ArenaModifier]
```

`MatchState.arena_id: str` (added on Arena introduction).

---

## 7. Balancing arenas

- Each new arena should change strategy **enough to matter** without making a single comp dominant. A modifier is too strong if any team archetype's win rate moves > 8 points from baseline on that arena.
- **No arena should buff or nerf a single character.** Buffs/nerfs target broad properties (mythology, skill kind, damage class) so the player can plan around them by drafting categories.
- Telemetry slices win rate by arena; rotation pulls underperforming arenas the next patch.

---

## 8. UI

- Arena name + 1-line modifier text shown during draft (see `docs/10-draft.md`).
- During match, a small badge in the corner shows the arena. Tooltip lists modifiers in plain language.
- Pre-game and post-game screens both display the arena prominently — this is the match's identity.

---

## 9. Open decisions

- [ ] Should there be a "no arena" baseline arena for tournaments / training? (MVP: yes — `id: neutral` with no modifiers.)
- [ ] Player veto / map ban during draft? (MVP: no, server picks alone.)
- [ ] Custom arenas in private lobbies? (Post-launch.)
