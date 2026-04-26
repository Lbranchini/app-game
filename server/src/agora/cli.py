"""CLI para simular partida bot vs bot.

Uso:
    agora-sim                    # 1 partida com seed default
    agora-sim --seed 7           # seed específica
    agora-sim --quiet            # só o resultado final
    agora-sim --runs 100         # estatísticas de N partidas
"""

from __future__ import annotations

import argparse
import random
import sys
from collections import Counter

from agora.data_loader import load_all_characters
from agora.game.engine import ESQUIVA_SKILL_ID, resolve_turn, start_match
from agora.schemas import (
    Action,
    Alvo,
    CharacterState,
    Essencia,
    MatchState,
    Personagem,
    PlayerSide,
    PlayerState,
)


def _bot_decide(
    state: MatchState,
    side: PlayerSide,
    characters: dict[str, Personagem],
    rng: random.Random,
) -> list[Action]:
    """IA simples: cada personagem usa a habilidade mais cara que pode pagar.

    Sem escolha de alvo refinada — escolhe inimigo vivo aleatório.
    """
    me = state.player(side)
    opp = state.oponente(side)
    actions: list[Action] = []
    essencias_disponiveis = dict(me.essencias)

    for char in me.personagens:
        if not char.vivo:
            continue
        if any(s.nome == "atordoado" for s in char.status):
            continue
        char_def = characters.get(char.id)
        if char_def is None:
            continue

        candidatas = sorted(char_def.habilidades, key=lambda h: -sum(h.custo.values()))
        chosen_action = None
        for skill in candidatas:
            if char.cooldowns.get(skill.id, 0) > 0:
                continue
            paid = _try_pagar(skill.custo, essencias_disponiveis)
            if paid is None:
                continue
            target_ids = _escolher_alvo(skill, char, me, opp, rng)
            if skill.alvo in (Alvo.INIMIGO_UNICO, Alvo.ALIADO_UNICO) and not target_ids:
                continue
            chosen_action = Action(
                char_id=char.id, skill_id=skill.id, target_ids=target_ids, paid=paid
            )
            for k, v in paid.items():
                essencias_disponiveis[k] = essencias_disponiveis.get(k, 0) - v
            break

        if chosen_action is None and essencias_disponiveis.get(Essencia.VIGOR, 0) + sum(
            essencias_disponiveis.values()
        ) >= 1:
            # tenta esquiva
            paid = _try_pagar({Essencia.GENERICA: 1}, essencias_disponiveis)
            if paid is not None:
                chosen_action = Action(
                    char_id=char.id, skill_id=ESQUIVA_SKILL_ID, target_ids=[], paid=paid
                )
                for k, v in paid.items():
                    essencias_disponiveis[k] = essencias_disponiveis.get(k, 0) - v

        if chosen_action is not None:
            actions.append(chosen_action)

    return actions


def _try_pagar(custo: dict[Essencia, int], disponiveis: dict[Essencia, int]) -> dict[Essencia, int] | None:
    """Tenta pagar o custo a partir das essências disponíveis. Retorna o paid ou None."""
    paid: dict[Essencia, int] = {}
    restante = dict(disponiveis)

    # Primeiro: paga custos específicos.
    for tipo, qtd in custo.items():
        if tipo == Essencia.GENERICA:
            continue
        if restante.get(tipo, 0) < qtd:
            return None
        paid[tipo] = paid.get(tipo, 0) + qtd
        restante[tipo] -= qtd

    # Depois: paga genéricas com qualquer cor.
    generica_qtd = custo.get(Essencia.GENERICA, 0)
    for tipo in [Essencia.VIGOR, Essencia.ESPIRITO, Essencia.MENTE, Essencia.SANGUE]:
        if generica_qtd <= 0:
            break
        usar = min(restante.get(tipo, 0), generica_qtd)
        if usar > 0:
            paid[tipo] = paid.get(tipo, 0) + usar
            restante[tipo] -= usar
            generica_qtd -= usar

    if generica_qtd > 0:
        return None
    return paid


def _escolher_alvo(
    skill,  # type: ignore[no-untyped-def]
    actor: CharacterState,
    me: PlayerState,
    opp: PlayerState,
    rng: random.Random,
) -> list[str]:
    if skill.alvo == Alvo.SI_MESMO:
        return [actor.id]
    if skill.alvo == Alvo.INIMIGO_UNICO:
        vivos = [c for c in opp.personagens if c.vivo]
        return [rng.choice(vivos).id] if vivos else []
    if skill.alvo == Alvo.ALIADO_UNICO:
        vivos = [c for c in me.personagens if c.vivo]
        return [rng.choice(vivos).id] if vivos else []
    return []


def _formatar_estado(state: MatchState) -> str:
    def _team(p: PlayerState) -> str:
        parts = []
        for c in p.personagens:
            tag = f"{c.nome}:{c.hp}/{c.hp_max}"
            if c.escudo > 0:
                tag += f"+{c.escudo}🛡"
            if not c.vivo:
                tag = f"💀 {c.nome}"
            parts.append(tag)
        ess = ",".join(f"{k.value[:3]}={v}" for k, v in p.essencias.items() if v > 0)
        return f"  [{p.side.value}] {' | '.join(parts)}  ({ess or '-'})"

    return f"Turno {state.turno} (vez de {state.jogador_atual.value})\n{_team(state.a)}\n{_team(state.b)}"


def simular_partida(seed: int, verbose: bool = True) -> PlayerSide | None:
    chars = load_all_characters()
    aquiles = chars["aquiles"]
    atena = chars["atena"]
    anubis = chars["anubis"]

    state = start_match(
        match_id=f"sim-{seed}",
        player_a_id="bot_a",
        team_a=[aquiles, atena, anubis],
        player_b_id="bot_b",
        team_b=[aquiles, atena, anubis],
        seed=seed,
    )
    rng = random.Random(seed)

    while not state.encerrado and state.turno < 100:
        if verbose:
            print(_formatar_estado(state))

        actions = _bot_decide(state, state.jogador_atual, chars, rng)
        if verbose:
            for a in actions:
                print(f"    -> {state.jogador_atual.value} {a.char_id}: {a.skill_id} {a.target_ids}")
        state, events = resolve_turn(state, actions, chars)
        if verbose:
            for ev in events:
                if ev.tipo in {"dano", "cura", "personagem_derrotado", "partida_encerrada"}:
                    print(f"      • {ev.tipo}: {ev.detalhes}")

    if verbose:
        print(_formatar_estado(state))
        print(f"\nVencedor: {state.vencedor.value if state.vencedor else 'empate'}")
    return state.vencedor


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--runs", type=int, default=1, help="Roda N partidas e mostra estatísticas")
    args = parser.parse_args(argv)

    if args.runs == 1:
        simular_partida(args.seed, verbose=not args.quiet)
        return 0

    counter: Counter[str] = Counter()
    for i in range(args.runs):
        winner = simular_partida(args.seed + i, verbose=False)
        counter[winner.value if winner else "empate"] += 1

    total = sum(counter.values())
    print(f"\nResultados de {total} partidas (seeds {args.seed}..{args.seed+total-1}):")
    for k in sorted(counter):
        pct = 100.0 * counter[k] / total
        print(f"  {k}: {counter[k]:4d} ({pct:5.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
