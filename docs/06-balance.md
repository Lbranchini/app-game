# 06 — Balance Philosophy

## Principles

1. **Everything has a counter.** No strategy may be undefeatable. Every dominant comp must have at least two documented counter-comps.
2. **Strong skills carry a clear cost.** High damage → high essence cost or long cooldown.
3. **Nerf by number, not by mechanic.** Tweaking values (damage, cooldown, cost) is safe. Changing how a skill works breaks player muscle memory.
4. **Iconic characters never become trash.** If Thor is too weak, raise him rather than benching him.
5. **Diversity > raw power.** A meta with five viable comps beats a meta with one dominant comp.

---

## Expected team archetypes

| Archetype | Concept | MVP examples |
|---|---|---|
| **Damage reduction** | Outlast, win in the long game | Joan + Athena + Isis |
| **AOE** | Pressure across all fronts | Thor + Anansi + Anubis |
| **Focus burst** | Pin a target and kill before reaction | Achilles + Sun Wukong + Athena |
| **Drain / control** | Deny opponent essence and turns | Quetzalcoatl + Anansi + Loki |
| **DoT / poison** | Win without needing to land much | Anubis + Achilles + Isis |
| **Wall** | Rotational invulnerability | Amaterasu + Joan + Athena |
| **Trick / reflect** | Bounce skills back | Loki + Cleopatra + Athena |
| **Mixed** | No clear shape, maximum flexibility | any combination |

Generic triangle: **Burst > Wall > Drain > Burst** (cyclical). Damage reduction breaks DoT. AOE breaks Wall.

---

## Balance metrics

Collected via telemetry; reviewed every patch.

| Metric | Healthy | Watch | Critical |
|---|---|---|---|
| Character pick rate | 5–25% | <2% or >40% | <1% or >60% |
| Character win rate | 47–53% | <44% or >56% | <40% or >60% |
| Comp win rate | 45–55% | <40% or >60% | <35% or >65% |
| Average match length | 8–12 min | 5–8 or 12–18 | <5 or >18 |

---

## Patch process

1. **Collect data** from the last two weeks (≥ 5,000 matches per character minimum).
2. **Identify outliers** (outside the watch/critical bounds).
3. **Propose changes** as a PR against `data/characters/*.yaml`. Diff is the audit trail.
4. **Internal playtest** (one 2h session with the team + beta friends).
5. **Public patch notes** explaining the *why* of each change.
6. **Deploy + monitor for one week** before the next patch.

---

## Anti-patterns to avoid

- ❌ "Buff everyone" to address one dominant character (power creep).
- ❌ Rewriting a character's core mechanic with no warning.
- ❌ Releasing a new character intentionally over-tuned to drive sales (paywall via balance).
- ❌ Ignoring qualitative Discord/Reddit feedback in favor of numbers alone.
- ❌ Emergency hotfixes without playtests — almost always make things worse.
