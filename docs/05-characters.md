# 05 — MVP Roster (16 characters)

> All public-domain figures (mythology or ancient history). Skills are **original** designs filling the classic archetypes of the 3v3 turn-based genre (burst, healer, tank, stunner, drainer, trickster, etc.) using the mechanical vocabulary defined in [`02-mechanics.md`](02-mechanics.md).

---

## Roster

| # | Character | Origin | Archetype | Primary essence |
|---|---|---|---|---|
| 1 | Achilles | Greek | Physical burst (with unique heel weakness) | Vigor |
| 2 | Athena | Greek | Defensive support + tactical buffs | Mind |
| 3 | Medusa | Greek | Long disable (petrification) | Mind |
| 4 | Thor | Norse | AOE / mass damage | Spirit |
| 5 | Loki | Norse | Trick / copy / reflect | Mind |
| 6 | Anubis | Egyptian | DoT (deadly poison) + finisher | Blood |
| 7 | Isis | Egyptian | Primary healer + affliction cleansing | Spirit |
| 8 | Sun Wukong | Chinese | Multi-hit / clones | Blood |
| 9 | Mulan | Chinese (historical) | Physical damage + stealth | Vigor |
| 10 | Amaterasu | Japanese | Damage buff + wall (shield) | Spirit |
| 11 | Quetzalcoatl | Aztec | Drainer (steals essence) | Mind |
| 12 | Anansi | African (Akan) | AOE stun / traps | Mind |
| 13 | Inanna | Mesopotamian | Hybrid heal + holy damage | Spirit |
| 14 | Joan of Arc | French historical | Tank / team damage reduction | Vigor |
| 15 | Cleopatra | Egyptian historical | Charm / target redirection | Mind |
| 16 | King Arthur | British | Leader / team buffs + executor | Vigor |

---

## Cultural coverage

| Culture | Characters |
|---|---|
| Greek | Achilles, Athena, Medusa |
| Norse | Thor, Loki |
| Egyptian | Anubis, Isis |
| Chinese | Sun Wukong, Mulan |
| Japanese | Amaterasu |
| Aztec | Quetzalcoatl |
| African (Akan) | Anansi |
| Mesopotamian | Inanna |
| Historical / legendary | Joan of Arc, Cleopatra, King Arthur |

10 distinct origins. Strong global appeal from launch.

---

## Archetype coverage

| Archetype | Characters |
|---|---|
| Physical burst | Achilles, Mulan, King Arthur |
| Magical burst / AOE | Thor |
| DoT / sustain damage | Anubis |
| Healer | Isis, Inanna |
| Tank / damage reduction | Joan of Arc, Athena, Amaterasu |
| Stun / disable | Medusa, Anansi |
| Behavior control | Cleopatra (charm), Loki (reflect) |
| Drainer (resource denial) | Quetzalcoatl |
| Trick / copy | Loki |
| Multi-hit | Sun Wukong |
| Team buff | Athena, Amaterasu, King Arthur |

All eight classic team-comp archetypes are covered by at least one character — most by two or more. Enables every team archetype defined in [`06-balance.md`](06-balance.md).

---

## Full skill specs — example (Achilles)

YAML lives at `data/characters/greek/achilles.yaml`. Summary:

**Achilles — Physical burst**
- Base HP: 110
- **Deadly Spear** (basic): 20 physical damage, cost 1 Vigor, no cooldown.
- **Myrmidon Charge** (secondary): 35 physical damage + Bleed (10/turn for 2 turns), cost 2 Vigor, cooldown 2.
- **Wrath of Peleus** (ultimate): for 3 turns, +15 outgoing damage and -10 incoming damage, cost 2 Vigor + 1 generic, cooldown 4.
- **Dodge** (universal): invulnerable for 1 turn.

---

## Summary specs — other 15

> Each needs a full YAML before the engine starts handling them. These are the core ideas + approximate cost/cooldown signaling weight.

### 2. Athena — Defensive support
HP 95.
- **Spear of Wisdom** (basic): 15 magical damage. 1 Mind. CD 0.
- **Counsel** (secondary): ally gains 15 damage reduction for 2 turns. 1 Mind + 1 generic. CD 2.
- **Aegis** (ultimate): all allies get a 25 HP destructible shield for 2 turns. 2 Mind + 2 generic. CD 5.

### 3. Medusa — Long disable
HP 90.
- **Unsettling Gaze** (basic): 15 magical damage + target gains "marked for petrification" (1 turn). 1 Mind. CD 0.
- **Serpent Hiss** (secondary): 25 damage; if target is marked, also stuns for 1 turn. 2 Mind. CD 2.
- **Petrification** (ultimate): stuns 1 target for 3 turns; target cannot become invulnerable during. 2 Mind + 2 generic. CD 6.

### 4. Thor — AOE
HP 105.
- **Mjolnir** (basic): 25 physical damage. 1 Vigor + 1 Spirit. CD 0.
- **Side Thunder** (secondary): 18 AOE damage to all enemies. 2 Spirit. CD 2.
- **Ragnarok** (ultimate): 35 AOE piercing damage; Thor is disarmed for 1 turn. 3 Spirit + 1 generic. CD 5.

### 5. Loki — Trickster
HP 85.
- **Golden Lie** (basic): 15 mental damage; target loses 1 random essence. 1 Mind. CD 0.
- **Shapeshift** (secondary): copies the next skill an ally uses (single-use next round). 1 Mind + 1 generic. CD 3.
- **Asgard's Deceit** (ultimate): next turn, all enemy attacks redirect to the caster. 2 Mind + 2 generic. CD 6.

### 6. Anubis — DoT
HP 95.
- **Choking Wraps** (basic): 10 damage + Poison (10/turn for 2 turns). 1 Blood. CD 0.
- **Sentence** (secondary): 20 damage; if target has poison, damage doubles. 1 Blood + 1 Mind. CD 2.
- **Heart's Burden** (ultimate): consumes target's remaining poison and converts it to immediate damage (10× turns left). 2 Blood + 1 generic. CD 5.

### 7. Isis — Healer
HP 95.
- **Mother's Hands** (basic): heal 20 HP on an ally. 1 Spirit. CD 0.
- **Protective Wings** (secondary): heal 15 HP + remove one affliction. 1 Spirit + 1 generic. CD 2.
- **Resurgence** (ultimate): lowest-HP ally recovers 50 HP + all afflictions cleared + Regen 10/turn for 2 turns. 2 Spirit + 2 generic. CD 6.

### 8. Sun Wukong — Multi-hit
HP 100.
- **Crescent Staff** (basic): 18 physical damage. 1 Vigor. CD 0.
- **Hair Clones** (secondary): 3 hits of 12 physical damage to chosen targets (same or different). 2 Vigor. CD 3.
- **Monkey King** (ultimate): 2 turns of stealth; first attack out of stealth deals triple damage and is piercing. 2 Blood + 1 Vigor. CD 5.

### 9. Mulan — Stealth burst
HP 100.
- **Hidden Sword** (basic): 18 physical damage; +5 if Mulan is stealthed. 1 Vigor. CD 0.
- **Disguise** (secondary): Mulan becomes stealthed for 2 turns. 1 Vigor + 1 generic. CD 3.
- **Family Honor** (ultimate): 40 piercing physical damage; if used while stealthed, ignores invulnerability. 2 Vigor + 1 generic. CD 5.

### 10. Amaterasu — Buff / wall
HP 95.
- **Solar Mirror** (basic): ally gains +10 outgoing damage for 2 turns. 1 Spirit. CD 0.
- **Eternal Morning** (secondary): team gains Regen 8/turn for 2 turns. 1 Spirit + 1 generic. CD 3.
- **Sacred Cave** (ultimate): the whole team is invulnerable for 1 turn. 3 Spirit + 2 generic. CD 7.

### 11. Quetzalcoatl — Drainer
HP 95.
- **Whispered Wind** (basic): 12 damage + drains 1 random essence from the opponent. 1 Mind. CD 0.
- **Sacred Plume** (secondary): 20 AOE damage; each target loses 1 random essence. 2 Mind. CD 3.
- **Sacred Breath** (ultimate): on the next turn, the opponent gains no essences. 2 Mind + 2 generic. CD 6.

### 12. Anansi — AOE stun
HP 90.
- **Spider Thread** (basic): 12 damage + target loses 1 random essence next turn. 1 Mind. CD 0.
- **Trap** (secondary): 1 enemy stunned for 1 turn. 2 Mind. CD 3.
- **Web of Lies** (ultimate): all enemies stunned for 1 turn. 3 Mind + 2 generic. CD 6.

### 13. Inanna — Hybrid
HP 95.
- **Spear of Dawn** (basic): 18 holy damage + heal 5 HP on an ally. 1 Spirit. CD 0.
- **Descent to the Underworld** (secondary): Inanna takes 15 fixed damage, but team gains +1 Spirit and Regen 10/turn for 2 turns. 1 Blood. CD 3.
- **The Queen Returns** (ultimate): heal 30 HP on an ally + 25 damage on an enemy. 2 Spirit + 1 Blood. CD 5.

### 14. Joan of Arc — Tank
HP 120.
- **Sacred Sword** (basic): 18 physical damage. 1 Vigor. CD 0.
- **Standard Raised** (secondary): Joan and 1 ally get 15 damage reduction for 2 turns. 1 Vigor + 1 generic. CD 3.
- **Vow of Orléans** (ultimate): for 1 turn, all damage to any ally is redirected to Joan at -50%. 2 Vigor + 2 generic. CD 6.

### 15. Cleopatra — Behavior control
HP 90.
- **Royal Decree** (basic): 15 mental damage + target cannot use their basic skill next turn. 1 Mind. CD 0.
- **Charm** (secondary): the target's next attack is redirected to one of their own allies (Cleopatra picks). 1 Mind + 1 generic. CD 3.
- **Queen of the Nile** (ultimate): for 1 turn, take full control of 1 enemy — on the opponent's turn, that enemy uses their basic skill on an ally of theirs (Cleopatra's choice). 3 Mind + 1 generic. CD 7.

### 16. King Arthur — Leader
HP 110.
- **Excalibur** (basic): 22 physical damage. 1 Vigor + 1 generic. CD 0.
- **Inspire Knights** (secondary): team gains +10 damage on physical attacks for 2 turns. 1 Vigor + 1 generic. CD 3.
- **Round Table** (ultimate): allies with HP lower than Arthur receive a 25 HP destructible shield; allies' cooldowns tick down +1. 2 Vigor + 2 generic. CD 6.

---

## Principles for new characters (post-MVP)

1. **Faithfulness to the myth** beats perfect balance — character first.
2. Each character needs **one clear weakness** (Achilles → heel; Sun Wukong → vulnerable outside stealth; Inanna → self-damage cost).
3. Every new skill must be explainable in **one sentence**.
4. Do **not** add new mechanics for a single character — reuse the vocabulary in [`07-glossary.md`](07-glossary.md).
5. **Cultural spread**: each wave of 4 new characters covers ≥ 3 different mythologies.
6. Use primary sources of mythology. Avoid recent pop-culture versions (which may still be protected).
