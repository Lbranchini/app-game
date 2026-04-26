"""Testes dos status effects: veneno, sangramento, escudo, redução, buff, invulnerável."""

from __future__ import annotations

from agora.game.engine import resolve_turn, start_match
from agora.schemas import Action, Essencia, Personagem


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


def test_veneno_aplica_dano_no_inicio_do_turno(all_characters: dict[str, Personagem]) -> None:
    state, chars = _setup(all_characters)
    # Anúbis (A) usa Bandagens em Aquiles (B) -> aplica veneno 10/turno por 2 turnos
    state.a.essencias[Essencia.SANGUE] = 1
    action = Action(char_id="anubis", skill_id="bandagens", target_ids=["aquiles"], paid={Essencia.SANGUE: 1})
    state_t1, _ = resolve_turn(state, [action], chars)

    aquiles_b = state_t1.b.personagens[0]
    # Recebe 10 de dano direto da Bandagens
    assert aquiles_b.hp == aquiles_b.hp_max - 10
    # Tem status de veneno
    assert any(s.nome == "veneno" for s in aquiles_b.status)

    # Próximo turno: jogador B age. Tick de status no início aplica 10 de veneno.
    state_t2, _ = resolve_turn(state_t1, [], chars)
    aquiles_b_2 = state_t2.b.personagens[0]
    assert aquiles_b_2.hp == aquiles_b.hp_max - 10 - 10


def test_veneno_expira_apos_duracao(all_characters: dict[str, Personagem]) -> None:
    state, chars = _setup(all_characters)
    state.a.essencias[Essencia.SANGUE] = 1
    action = Action(char_id="anubis", skill_id="bandagens", target_ids=["aquiles"], paid={Essencia.SANGUE: 1})
    state = resolve_turn(state, [action], chars)[0]
    # turno B (tick 1)
    state = resolve_turn(state, [], chars)[0]
    # turno A (tick 2 -> expira)
    state = resolve_turn(state, [], chars)[0]
    aquiles_b = state.b.personagens[0]
    assert all(s.nome != "veneno" for s in aquiles_b.status), "Veneno deve ter expirado"


def test_reducao_dano_subtrai_do_dano_recebido(all_characters: dict[str, Personagem]) -> None:
    state, chars = _setup(all_characters)
    # Atena (A) dá Conselho a Aquiles aliado (A) -> +15 redução por 2 turnos
    state.a.essencias[Essencia.MENTE] = 1
    state.a.essencias[Essencia.VIGOR] = 1  # 1 generica via vigor
    conselho = Action(
        char_id="atena", skill_id="conselho", target_ids=["aquiles"],
        paid={Essencia.MENTE: 1, Essencia.VIGOR: 1},
    )
    state = resolve_turn(state, [conselho], chars)[0]

    # Turno B: ataca Aquiles A com Lança (20 de dano)
    state.b.essencias[Essencia.VIGOR] = 1
    lanca = Action(char_id="aquiles", skill_id="lanca", target_ids=["aquiles"], paid={Essencia.VIGOR: 1})
    state = resolve_turn(state, [lanca], chars)[0]

    aquiles_a = state.a.personagens[0]
    # 20 - 15 redução = 5 de dano
    assert aquiles_a.hp == aquiles_a.hp_max - 5


def test_escudo_destrutivel_absorve_antes_do_hp(all_characters: dict[str, Personagem]) -> None:
    state, chars = _setup(all_characters)
    state.a.essencias[Essencia.MENTE] = 2
    state.a.essencias[Essencia.VIGOR] = 2  # como genérica
    egide = Action(
        char_id="atena", skill_id="egide", target_ids=[],
        paid={Essencia.MENTE: 2, Essencia.VIGOR: 2},
    )
    state = resolve_turn(state, [egide], chars)[0]

    aquiles_a = state.a.personagens[0]
    assert aquiles_a.escudo == 25

    state.b.essencias[Essencia.VIGOR] = 1
    lanca = Action(char_id="aquiles", skill_id="lanca", target_ids=["aquiles"], paid={Essencia.VIGOR: 1})
    state = resolve_turn(state, [lanca], chars)[0]
    aquiles_a = state.a.personagens[0]
    # Dano 20, escudo absorve 20, escudo restante 5
    assert aquiles_a.escudo == 5
    assert aquiles_a.hp == aquiles_a.hp_max


def test_buff_dano_soma_no_ataque(all_characters: dict[str, Personagem]) -> None:
    state, chars = _setup(all_characters)
    state.a.essencias[Essencia.VIGOR] = 3
    state.a.essencias[Essencia.MENTE] = 1  # como genérica para fúria
    # Aquiles A usa Fúria em si mesmo (turno A1)
    furia = Action(
        char_id="aquiles", skill_id="furia", target_ids=[],
        paid={Essencia.VIGOR: 2, Essencia.MENTE: 1},
    )
    state = resolve_turn(state, [furia], chars)[0]

    # Turno B: passa
    state = resolve_turn(state, [], chars)[0]

    # Turno A: lança ainda com fúria ativa (durou 3 turnos, tickou 1 -> resta 2)
    state.a.essencias[Essencia.VIGOR] = 1
    lanca = Action(char_id="aquiles", skill_id="lanca", target_ids=["aquiles"], paid={Essencia.VIGOR: 1})
    state = resolve_turn(state, [lanca], chars)[0]
    aquiles_b = state.b.personagens[0]
    # 20 (lança) + 15 (buff_dano) = 35
    assert aquiles_b.hp == aquiles_b.hp_max - 35


def test_perfurante_ignora_reducao_dano(all_characters: dict[str, Personagem]) -> None:
    state, chars = _setup(all_characters)
    # Atena B dá Conselho ao Aquiles B
    state.b.essencias[Essencia.MENTE] = 1
    state.b.essencias[Essencia.VIGOR] = 1
    # Turno A passa
    state = resolve_turn(state, [], chars)[0]
    # Turno B: conselho
    conselho = Action(
        char_id="atena", skill_id="conselho", target_ids=["aquiles"],
        paid={Essencia.MENTE: 1, Essencia.VIGOR: 1},
    )
    state = resolve_turn(state, [conselho], chars)[0]
    # Turno A: Anúbis usa Pesar do Coração (perfurante) em Aquiles B
    state.a.essencias[Essencia.SANGUE] = 2
    state.a.essencias[Essencia.MENTE] = 1
    pesar = Action(
        char_id="anubis", skill_id="pesar", target_ids=["aquiles"],
        paid={Essencia.SANGUE: 2, Essencia.MENTE: 1},
    )
    state = resolve_turn(state, [pesar], chars)[0]
    aquiles_b = state.b.personagens[0]
    # 30 perfurante, ignora 15 redução -> 30
    assert aquiles_b.hp == aquiles_b.hp_max - 30
