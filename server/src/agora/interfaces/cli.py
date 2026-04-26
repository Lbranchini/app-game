"""Bot-vs-bot match simulator.

Usage:
    agora-sim                       # 1 match with default seed
    agora-sim --seed 7              # specific seed
    agora-sim --quiet               # only the final result
    agora-sim --runs 100            # statistics across N matches
"""

from __future__ import annotations

import argparse
import random
import sys
from collections import Counter

from agora.application.ports import CharacterRepository, RandomSource
from agora.application.use_cases import (
    DODGE_SKILL_ID,
    resolve_turn,
    start_match,
)
from agora.domain.character import Character, Skill
from agora.domain.enums import Essence, Side, TargetKind
from agora.domain.match import Action, CharacterState, MatchState, PlayerState
from agora.infrastructure.seeded_random import SeededRandom
from agora.infrastructure.yaml_repository import YamlCharacterRepository


def _bot_choose_actions(
    state: MatchState,
    side: Side,
    repository: CharacterRepository,
    rng: random.Random,
) -> list[Action]:
    """Naive bot: each character picks the most expensive affordable skill.

    Selects a random alive enemy when targeting is required. Falls back to
    Dodge if nothing else fits.
    """
    me = state.player(side)
    opp = state.opponent(side)
    actions: list[Action] = []
    available = dict(me.essences)

    for character in me.characters:
        if not character.alive:
            continue
        if any(s.name == "stun" for s in character.statuses):
            continue
        try:
            character_def = repository.get(character.id)
        except KeyError:
            continue

        candidates = sorted(character_def.skills, key=lambda s: -sum(s.cost.values()))
        chosen: Action | None = None
        for skill in candidates:
            if character.cooldowns.get(skill.id, 0) > 0:
                continue
            paid = _try_pay(skill.cost, available)
            if paid is None:
                continue
            target_ids = _pick_targets(skill, character, me, opp, rng)
            if skill.target in {TargetKind.SINGLE_ENEMY, TargetKind.SINGLE_ALLY} and not target_ids:
                continue
            chosen = Action(
                character_id=character.id,
                skill_id=skill.id,
                target_ids=target_ids,
                paid=paid,
            )
            for k, v in paid.items():
                available[k] = available.get(k, 0) - v
            break

        if chosen is None:
            paid = _try_pay({Essence.GENERIC: 1}, available)
            if paid is not None:
                chosen = Action(
                    character_id=character.id,
                    skill_id=DODGE_SKILL_ID,
                    target_ids=[],
                    paid=paid,
                )
                for k, v in paid.items():
                    available[k] = available.get(k, 0) - v

        if chosen is not None:
            actions.append(chosen)

    return actions


def _try_pay(
    cost: dict[Essence, int], available: dict[Essence, int]
) -> dict[Essence, int] | None:
    """Try to pay a cost from the supplied pool. Return the payment or None."""
    paid: dict[Essence, int] = {}
    remaining = dict(available)

    for kind, qty in cost.items():
        if kind is Essence.GENERIC:
            continue
        if remaining.get(kind, 0) < qty:
            return None
        paid[kind] = paid.get(kind, 0) + qty
        remaining[kind] -= qty

    generic_qty = cost.get(Essence.GENERIC, 0)
    for kind in (Essence.VIGOR, Essence.SPIRIT, Essence.MIND, Essence.BLOOD):
        if generic_qty <= 0:
            break
        use = min(remaining.get(kind, 0), generic_qty)
        if use > 0:
            paid[kind] = paid.get(kind, 0) + use
            remaining[kind] -= use
            generic_qty -= use

    if generic_qty > 0:
        return None
    return paid


def _pick_targets(
    skill: Skill,
    actor: CharacterState,
    me: PlayerState,
    opp: PlayerState,
    rng: random.Random,
) -> list[str]:
    if skill.target is TargetKind.SELF:
        return [actor.id]
    if skill.target is TargetKind.SINGLE_ENEMY:
        alive = [c for c in opp.characters if c.alive]
        return [rng.choice(alive).id] if alive else []
    if skill.target is TargetKind.SINGLE_ALLY:
        alive = [c for c in me.characters if c.alive]
        return [rng.choice(alive).id] if alive else []
    return []


def _format_state(state: MatchState) -> str:
    def _team(p: PlayerState) -> str:
        parts = []
        for c in p.characters:
            tag = f"{c.name}:{c.hp}/{c.hp_max}"
            if c.shield > 0:
                tag += f"+{c.shield}*shield"
            if not c.alive:
                tag = f"X {c.name}"
            parts.append(tag)
        ess = ",".join(f"{k.value[:3]}={v}" for k, v in p.essences.items() if v > 0)
        return f"  [{p.side.value}] {' | '.join(parts)}  ({ess or '-'})"

    return (
        f"Turn {state.turn} (active: {state.current_side.value})\n"
        f"{_team(state.a)}\n{_team(state.b)}"
    )


def simulate_match(seed: int, *, verbose: bool = True) -> Side | None:
    repository = YamlCharacterRepository()
    characters = repository.all()
    teamA: list[Character] = [characters["achilles"], characters["athena"], characters["anubis"]]
    teamB: list[Character] = [characters["achilles"], characters["athena"], characters["anubis"]]

    rng_source: RandomSource = SeededRandom(seed)
    state = start_match(
        match_id=f"sim-{seed}",
        player_a_id="bot_a",
        team_a=teamA,
        player_b_id="bot_b",
        team_b=teamB,
        rng=rng_source,
        seed=seed,
    )
    target_rng = random.Random(seed)

    while not state.finished and state.turn < 100:
        if verbose:
            print(_format_state(state))

        actions = _bot_choose_actions(state, state.current_side, repository, target_rng)
        if verbose:
            for a in actions:
                print(f"    -> {state.current_side.value} {a.character_id}: {a.skill_id} {a.target_ids}")

        state, events = resolve_turn(state, actions, repository, rng_source)
        if verbose:
            for ev in events:
                if ev.kind in {"damage", "heal", "character_defeated", "match_finished"}:
                    print(f"      * {ev.kind}: {ev.details}")

    if verbose:
        print(_format_state(state))
        winner = state.winner.value if state.winner else "draw"
        print(f"\nWinner: {winner}")
    return state.winner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--runs", type=int, default=1)
    args = parser.parse_args(argv)

    if args.runs == 1:
        simulate_match(args.seed, verbose=not args.quiet)
        return 0

    counts: Counter[str] = Counter()
    for i in range(args.runs):
        winner = simulate_match(args.seed + i, verbose=False)
        counts[winner.value if winner else "draw"] += 1

    total = sum(counts.values())
    print(f"\nResults across {total} matches (seeds {args.seed}..{args.seed + total - 1}):")
    for k in sorted(counts):
        pct = 100.0 * counts[k] / total
        print(f"  {k}: {counts[k]:4d} ({pct:5.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
