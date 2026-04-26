"""Testes da engine: dano, custos, cooldowns, alvos."""

from __future__ import annotations

from agora.game.engine import resolve_turn, start_match
from agora.schemas import Action, Essencia, Personagem, PlayerSide


def _setup(all_characters: dict[str, Personagem]) -> tuple:
    aquiles = all_characters["aquiles"]
    atena = all_characters["atena"]
    anubis = all_characters["anubis"]
    state = start_match(
        match_id="m1",
        player_a_id="p1",
        team_a=[aquiles, atena, anubis],
        player_b_id="p2",
        team_b=[aquiles, atena, anubis],
        seed=42,
    )
    return state, all_characters


def test_partida_inicia_com_essencias_iniciais(all_characters: dict[str, Personagem]) -> None:
    state, _ = _setup(all_characters)
    total_a = sum(state.a.essencias.values())
    total_b = sum(state.b.essencias.values())
    assert total_a == 1, "Jogador A começa com 1 essência"
    assert total_b == 3, "Jogador B começa com 3 essências"
    for char in state.a.personagens:
        assert char.hp == char.hp_max


def test_lanca_causa_20_de_dano(all_characters: dict[str, Personagem]) -> None:
    state, chars = _setup(all_characters)
    state.a.essencias[Essencia.VIGOR] = 1
    state.a.essencias[Essencia.MENTE] = 0
    state.a.essencias[Essencia.SANGUE] = 0
    state.a.essencias[Essencia.ESPIRITO] = 0

    action = Action(char_id="aquiles", skill_id="lanca", target_ids=["aquiles"], paid={Essencia.VIGOR: 1})
    new_state, events = resolve_turn(state, [action], chars)

    alvo = new_state.b.personagens[0]
    assert alvo.hp == alvo.hp_max - 20
    assert any(e.tipo == "dano" and e.detalhes.get("valor") == 20 for e in events)


def test_essencia_insuficiente_acao_invalida(all_characters: dict[str, Personagem]) -> None:
    state, chars = _setup(all_characters)
    for e in [Essencia.VIGOR, Essencia.MENTE, Essencia.SANGUE, Essencia.ESPIRITO]:
        state.a.essencias[e] = 0

    action = Action(char_id="aquiles", skill_id="lanca", target_ids=["aquiles"], paid={Essencia.VIGOR: 1})
    _, events = resolve_turn(state, [action], chars)
    assert any(e.tipo == "acao_invalida" and e.detalhes.get("motivo") == "essencia_insuficiente" for e in events)


def test_cooldown_aplicado_e_decrementa(all_characters: dict[str, Personagem]) -> None:
    state, chars = _setup(all_characters)
    state.a.essencias[Essencia.VIGOR] = 2

    action = Action(char_id="aquiles", skill_id="investida", target_ids=["aquiles"], paid={Essencia.VIGOR: 2})
    new_state, _ = resolve_turn(state, [action], chars)

    aquiles_a = new_state.a.personagens[0]
    # Cooldown era 2; turno do A já passou (decrementou 1) -> resta 1
    assert aquiles_a.cooldowns.get("investida") == 1


def test_jogador_alterna_a_cada_turno(all_characters: dict[str, Personagem]) -> None:
    state, chars = _setup(all_characters)
    new_state, _ = resolve_turn(state, [], chars)
    assert new_state.jogador_atual == PlayerSide.B
    new_state2, _ = resolve_turn(new_state, [], chars)
    assert new_state2.jogador_atual == PlayerSide.A


def test_alvo_invalido_nao_aplica_efeito(all_characters: dict[str, Personagem]) -> None:
    state, chars = _setup(all_characters)
    state.a.essencias[Essencia.VIGOR] = 1

    # alvo "fake" não existe na equipe inimiga
    action = Action(char_id="aquiles", skill_id="lanca", target_ids=["nao_existe"], paid={Essencia.VIGOR: 1})
    new_state, _ = resolve_turn(state, [action], chars)
    # Nenhum dano causado
    for c in new_state.b.personagens:
        assert c.hp == c.hp_max
