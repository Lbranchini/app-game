# 09 — Missions and Progression (character unlocks)

> Career-style progression: a starter pool is unlocked from first login; the rest are earned by completing **missions** that nudge the player toward mechanics and archetypes they might otherwise skip.

---

## 1. Principles

1. **Smooth onboarding.** The starter pool covers **all** core archetypes — a new player never feels they have to pay for variety.
2. **Missions teach the game.** Every mission exposes the player to a mechanic (stun, heal, drain, AOE...) they might not naturally use.
3. **No pay-to-skip.** Unlockable characters are obtained **only** through gameplay. Cosmetics may be sold; characters never are.
4. **Reasonable pace.** A character should unlock in ~10–30 matches if a player focuses on them. No grind walls.
5. **Missions are cumulative.** Progress carries between matches. Nothing is "all-or-nothing" within a single match unless explicitly flagged.

---

## 2. Roster: starters vs unlockables

### Unlocked from login (8 characters)

Cover all 8 classic archetypes; allow any basic comp.

| Character | Archetype |
|---|---|
| Achilles | Physical burst |
| Athena | Defensive support / buff |
| Thor | AOE |
| Anubis | DoT |
| Isis | Healer |
| Anansi | Stunner |
| Joan of Arc | Tank |
| Loki | Trickster / copy |

### Unlockable via missions (8 characters)

Specialized variants of the basic archetypes — a lateral upgrade, not a vertical one. They aren't *better*; they're *different*.

| Character | Archetype variant | Specialty added |
|---|---|---|
| Medusa | Long stun | 3-turn disable with conditions |
| Sun Wukong | Multi-hit | Multiple targets or multiple hits |
| Mulan | Stealth burst | Stealth + piercing combos |
| Amaterasu | Wall + buff | Whole-team invulnerability |
| Quetzalcoatl | Drainer | Resource denial |
| Inanna | Hybrid | Heal + damage in one |
| Cleopatra | Behavior control | Charm / attack redirection |
| King Arthur | Leader | Team-wide buffs that scale |

---

## 3. Mission shape

Each unlockable character has **3 missions**. All three must complete to unlock.

```yaml
# data/missions/medusa.yaml
character_unlock: medusa
missions:
  - id: medusa_1
    title: "The gaze paralyzes"
    description: "Stun 50 enemies across your career."
    counter: status_applied.stun
    target: 50
  - id: medusa_2
    title: "Tactical wisdom"
    description: "Win 10 matches with Athena on your team."
    counter: wins_with.athena
    target: 10
  - id: medusa_3
    title: "Total silence"
    description: "Win 5 matches in which no enemy used an ultimate."
    counter: wins_with_condition.no_enemy_ultimate
    target: 5
```

### Counter kinds supported

| Kind | Example | How it ticks |
|---|---|---|
| `cumulative_simple` | `total_damage_dealt` | +N per hit |
| `event_count` | `status_applied.poison` | +1 each application |
| `wins_with.<character>` | `wins_with.achilles` | +1 per win with Achilles on the team |
| `wins_with_condition.<cond>` | `vigor_only_comp` | +1 per win that satisfies the condition |
| `unique_milestone` | `unlock_inanna` | binary (done / not) |

Counters live in `players.progress` (JSONB) or in a dedicated `player_counters` table — decision deferred to Phase 1 implementation.

---

## 4. Full mission catalog

### Medusa — Long disable
1. **The gaze paralyzes** — Stun 50 enemies.
2. **Tactical wisdom** — Win 10 matches with Athena on your team.
3. **Total silence** — Win 5 matches with no enemy ultimate landing.

### Sun Wukong — Multi-hit
1. **Tireless staff** — Land 200 basic skills.
2. **Olympic fists** — Deal 5,000 cumulative physical damage.
3. **Warrior team** — Win 10 matches with a Vigor-only comp.

### Mulan — Stealth burst
1. **First strike** — Deal 3,000 damage with the first action of any turn.
2. **Lightning win** — Win 5 matches in ≤ 8 turns.
3. **Surgical strike** — Defeat 25 enemies with piercing skills.

### Amaterasu — Wall / buff
1. **Caring for yours** — Heal 2,000 HP total with Isis.
2. **Team intact** — Win 5 matches with no ally KOs.
3. **Rising sun** — Apply 100 buffs to allies.

### Quetzalcoatl — Drainer
1. **Mystery thief** — Drain 200 essences from opponents.
2. **Master of deceit** — Win 10 matches with Loki on your team.
3. **Tactical asphyxia** — Win 5 matches in which the opponent ended a turn at 0 essences.

### Inanna — Hybrid
1. **The scales** — Deal 2,000 damage *and* heal 2,000 HP cumulatively.
2. **Double blessing** — Win 10 matches with Isis on your team.
3. **Balanced comp** — Win 5 matches with a 1 healer + 2 damage dealers comp.

### Cleopatra — Behavior control
1. **Manipulator** — Use stun/charm/silence skills 50 times.
2. **Perfect defense** — Win 5 matches with no enemy ultimate landing on you.
3. **String weaver** — Win 10 matches with Anansi on your team.

### King Arthur — Leader
1. **Agora veteran** — Win 25 matches (any comp).
2. **Round table** — Win 10 matches with all 3 characters surviving.
3. **Knighthood** — Reach Elo 1300+.

---

## 5. UI sketch

```
┌─────────────────────────────────────────┐
│  CHARACTERS                             │
├─────────────────────────────────────────┤
│  Available (8/16)                       │
│  [Achilles][Athena][Thor][Anubis]...    │
│                                         │
│  Locked                                 │
│  ┌──────────────────────────────────┐   │
│  │ [LOCKED] MEDUSA                  │   │
│  │  ###--   Stun 50 (32/50)         │   │
│  │  #####   Win with Athena (10/10) │   │
│  │  ##---   No ultimates (2/5)      │   │
│  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────┐   │
│  │ [LOCKED] SUN WUKONG              │   │
│  │  ...                             │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

An achievement-style notification when all three complete.

---

## 6. Server-side implementation

### Per-match flow

```
1. Match ends (server already knows winner + final state)
2. Telemetry collector emits an event:
   {
     match_id, player_id,
     damage_dealt: 2150,
     statuses_applied: { stun: 3, poison: 8 },
     team: [achilles, athena, anansi],
     allies_alive: 3,
     result: win,
     turns: 11,
     ...
   }
3. MissionService consumes the event:
   - Increments matching counters in players.progress
   - For each locked character, checks whether the 3 missions are met
   - If yes, marks the character unlocked and emits an unlock event
4. Client receives updated state + a push notification "<X> unlocked!"
```

### Schema

```sql
ALTER TABLE players ADD COLUMN unlocked_characters JSONB
  NOT NULL DEFAULT '["achilles","athena","thor","anubis","isis","anansi","joan","loki"]';

ALTER TABLE players ADD COLUMN progress JSONB NOT NULL DEFAULT '{}';
-- e.g. {"total_damage_dealt": 14230, "status_applied.stun": 32, ...}
```

JSONB counters are simple in MVP. Migrate to a dedicated table only if queries get slow (unlikely — these are write-on-event, not query-heavy).

### Where it runs

`MissionService` is a pure Python module called **after** the engine resolves the final turn. Non-blocking — can run in an `arq` worker if it grows.

---

## 7. Trade-offs

- **Why 3 missions per character (not 1 or 5)?** 1 is grindy. 5 is a wall. 3 is variety without exhaustion.
- **Why no rotating daily missions in MVP?** They add state-per-day complexity without core value. v0.5.
- **What if a player wants to skip?** No paid shortcut in MVP. A future Battle Pass could include cosmetic + 1 ticket per season — but never direct character sales.
- **Post-MVP characters** ship with their own thematic 3-mission set.

---

## 8. Roadmap impact

Adds **+1 to +2 weeks** to Phase 3 (Multiplayer + accounts):
- Progress + unlocked-characters schema
- MissionService + per-match telemetry plumbing
- "Characters" UI with progress bars

No impact on Phase 1 (engine of rules) or Phase 2 (local web client — all 16 unlocked there for testing).
