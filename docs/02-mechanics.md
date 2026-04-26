# 02 — Game Mechanics

> Technical specification of the rules. Adapted to our mythological theme with proprietary naming.

---

## 1. Match structure

- **Format:** 3v3, alternating turns, asynchronous or real-time PvP.
- **Win condition:** reduce all three of your opponent's characters to 0 HP.
- **Draw / time limit:** 60 turns max. Beyond that, whoever has more total HP wins; ties go to the defender.
- **Base HP per character:** 100 ± archetype offsets.

### Turn flow

```
1. Turn start
   ├── Cooldowns on the active side decrement by 1
   ├── Status effects tick (DoT, HoT, expirations)
   └── Active player rolls N essences (N = alive characters)

2. Planning
   ├── Pick one skill per character
   ├── Pick targets (enemy, ally, self)
   ├── Pay essence cost
   └── Reorder action queue (drag and drop)

3. Confirm ("READY")
   └── If not confirmed within 60s, the turn passes empty

4. Resolution
   ├── Skills resolve in queued order
   ├── Animations + math
   └── New statuses applied

5. Turn end → opponent's turn
```

---

## 2. Essence system (energy)

Four colors plus a generic slot.

| Type | Color | Theme |
|---|---|---|
| **Vigor** | Red | Physical force, melee combat |
| **Spirit** | Blue | Arcane magic, elemental control |
| **Mind** | White | Illusion, manipulation, knowledge |
| **Blood** | Green | Divine lineage, transformation, innate gifts |

### Generation

- At each turn start, the active side rolls **1 random essence per alive character** (3 at full team, fewer as characters fall).
- **Exception:** the side that goes first only rolls **1** on turn 1; the second side rolls **3** (compensates the initiative disadvantage).
- Essences **stack** between turns (suggested cap: 30 to prevent abuse).

### Skill costs

- Each skill has a cost, e.g. `2 Vigor + 1 Generic`.
- **Generic** = any color (you choose what to spend).
- **Trade essence:** spend **5 essences of any color** to receive **1 of the chosen color** (limit 1 trade per turn; mitigates RNG swings).

---

## 3. Skills

Each character has **4 skill slots**:

1. **Basic** (cost 0–1, no or short cooldown)
2. **Secondary** (medium cost, cooldown 2–3)
3. **Ultimate** (high cost, cooldown 4–6)
4. **Dodge** (universal defense: invulnerable for 1 turn, cost 1 generic, cooldown 4 — every character has it)

### Execution kinds

| Kind | Behavior |
|---|---|
| **Instant** | Resolves immediately; no further link to the user. Not cancelled if user is later stunned. |
| **Ongoing** | Lasts N turns. If user is stunned the effect **pauses** and resumes after. If target becomes invulnerable the skill **does not land** during invulnerability but continues afterward. |
| **Control** | Like Ongoing, but **breaks** if the link between user and target is lost (stun, death, target invulnerable). Useful for "grab" effects. |

### Targeting

- **Single enemy**
- **All enemies** (AOE)
- **Single ally**
- **All allies**
- **Self**
- **Random** (rare; usually high-risk ultimates)

### Secondary tags

- **Physical** vs **Magical** (interacts with specific reductions).
- **Melee** vs **Ranged** (some defenses block only one).
- **Unique** (cannot be used more than once per match — only epic ultimates).

---

## 4. Status effects

### Afflictions (negative)

| Effect | What it does |
|---|---|
| **Stun** | Cannot use skills or dodge. Ongoing skills pause. |
| **Silence** | Cannot use **magical** skills. |
| **Disarm** | Cannot use **physical** skills. |
| **Poison (DoT)** | Takes X damage at turn start for N turns. |
| **Bleed** | Takes damage proportional to damage **dealt** last turn. |
| **Drained** | Team loses 1 random essence at turn start. |
| **Marked** | Takes +X% damage from specific sources. |
| **Vulnerable** | Cannot become invulnerable or gain damage reduction. |

### Blessings (positive)

| Effect | What it does |
|---|---|
| **Invulnerable** | Immune to direct enemy skills (typically 1 turn). |
| **Damage reduction** | Receives X less damage per hit. |
| **Destructible shield** | A pool of HP that absorbs damage until broken. |
| **Regen (HoT)** | Heals X HP per turn for N turns. |
| **Stealth** | Enemies cannot target until the character attacks. |
| **Reflective** | Next enemy skill is bounced back. |

### Special modifiers

- **Piercing** — ignores damage reduction and destructible shield.
- **True** — ignores invulnerability.
- **Inevitable** — ignores dodges and reflects.
- **Copy** — user copies a skill from the target for their own use.

---

## 5. Character anatomy (data shape)

```yaml
id: achilles
name: Achilles
mythology: Greek
archetype: damage_dealer
base_hp: 110
skills:
  - id: spear
    name: "Deadly Spear"
    cost: { vigor: 1 }
    cooldown: 0
    kind: instant
    target: single_enemy
    effects:
      - { kind: damage, value: 20, damage_class: physical }
  - id: charge
    name: "Myrmidon Charge"
    cost: { vigor: 2 }
    cooldown: 2
    kind: instant
    target: single_enemy
    effects:
      - { kind: damage, value: 35, damage_class: physical }
      - { kind: status, status: bleed, duration: 2, value: 10 }
  - id: wrath
    name: "Wrath of Peleus"
    cost: { vigor: 2, generic: 1 }
    cooldown: 4
    kind: ongoing
    duration: 3
    target: self
    effects:
      - { kind: damage_buff, value: 15, duration: 3 }
      - { kind: damage_reduction, value: 10, duration: 3 }
```

---

## 6. Resolution priority

Action order **matters**. Default: queue order chosen by the active player, with these overrides:

1. **Reflect and counter** trigger **before** the responding skills.
2. **Invulnerability and defense** apply **before** same-turn attacks.
3. **Heals** resolve **after** damage (so they aren't wasted).
4. Within each category, manual order from the player.

---

## 7. Game modes (planned)

| Mode | Description | Phase |
|---|---|---|
| **Training** | vs. AI, no ranking. | MVP |
| **Ranked** | PvP with Elo. | MVP |
| **Casual** | PvP without Elo. | v0.5 |
| **Daily missions** | e.g. "Win 3 matches with a Greek character". | v0.5 |
| **Seasonal tournaments** | Fixed brackets with cosmetic prizes. | v1.0 |
| **3v3v3 co-op** | Two teams vs. an AI boss. | v1.5 |

---

## 8. Open decisions

- [ ] Per-turn time limit: 45s or 60s?
- [ ] Allow reconnect in ranked?
- [ ] Character ban-pick in ranked (MOBA-style)?
- [ ] MVP roster size: 12 or 16 characters? (Decided: **16**.)
