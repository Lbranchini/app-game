"""Engine determinística de resolução de turnos.

Contrato:
  start_match(player_a_id, team_a, player_b_id, team_b, seed) -> MatchState
  resolve_turn(state, actions, characters) -> (new_state, events)

A engine NÃO faz I/O. Recebe estado + ações, devolve novo estado + log de eventos.
"""

from __future__ import annotations

import copy

from agora.game.rng import SeededRng
from agora.schemas import (
    Action,
    Alvo,
    CharacterState,
    Efeito,
    Essencia,
    Event,
    Habilidade,
    MatchState,
    Personagem,
    PlayerSide,
    PlayerState,
    StatusAtivo,
    TipoEfeito,
)

# Habilidade universal de esquiva (ID reservado).
ESQUIVA_SKILL_ID = "esquiva"
ESQUIVA: Habilidade = Habilidade(
    id=ESQUIVA_SKILL_ID,
    nome="Esquivar",
    tipo="instantanea",  # type: ignore[arg-type]
    custo={Essencia.GENERICA: 1},
    cooldown=4,
    alvo=Alvo.SI_MESMO,
    efeitos=[Efeito(tipo=TipoEfeito.INVULNERAVEL, duracao=1)],
)

# Tipos de essência que podem ser sorteadas (não inclui GENERICA).
ESSENCIAS_SORTEAVEIS = [Essencia.VIGOR, Essencia.ESPIRITO, Essencia.MENTE, Essencia.SANGUE]


# --------------------------------------------------------------------------- #
# Setup                                                                       #
# --------------------------------------------------------------------------- #


def start_match(
    match_id: str,
    player_a_id: str,
    team_a: list[Personagem],
    player_b_id: str,
    team_b: list[Personagem],
    seed: int = 0,
) -> MatchState:
    """Cria o estado inicial. Jogador A começa com 1 essência; B começa com 3."""
    if len(team_a) != 3 or len(team_b) != 3:
        raise ValueError("Cada equipe precisa ter exatamente 3 personagens")

    state = MatchState(
        match_id=match_id,
        a=PlayerState(
            id=player_a_id,
            side=PlayerSide.A,
            personagens=[_new_char_state(c) for c in team_a],
        ),
        b=PlayerState(
            id=player_b_id,
            side=PlayerSide.B,
            personagens=[_new_char_state(c) for c in team_b],
        ),
        rng_seed=seed,
    )
    rng = SeededRng(seed)
    _gerar_essencias(state.a, 1, rng)
    _gerar_essencias(state.b, 3, rng)
    return state


def _new_char_state(p: Personagem) -> CharacterState:
    return CharacterState(id=p.id, nome=p.nome, hp=p.hp_base, hp_max=p.hp_base)


# --------------------------------------------------------------------------- #
# Turno                                                                       #
# --------------------------------------------------------------------------- #


def resolve_turn(
    state: MatchState,
    actions: list[Action],
    characters: dict[str, Personagem],
) -> tuple[MatchState, list[Event]]:
    """Resolve o turno do jogador atual.

    Ordem:
      1. Tick de status (DoT, expiração de buffs).
      2. Validação + execução das ações na ordem informada.
      3. Decremento de cooldowns.
      4. Checagem de vitória.
      5. Troca de jogador atual + geração de essências para o novo atual.
    """
    if state.encerrado:
        raise RuntimeError("Partida já encerrada")

    new_state = copy.deepcopy(state)
    events: list[Event] = []
    rng = SeededRng(new_state.rng_seed + new_state.turno * 1000)

    atual = new_state.player(new_state.jogador_atual)
    oponente = new_state.oponente(new_state.jogador_atual)

    events.append(
        Event(
            tipo="turno_iniciado",
            detalhes={"turno": new_state.turno, "jogador": atual.side.value},
        )
    )

    _tick_status(atual, events)
    _tick_status(oponente, events)
    if _checar_encerramento(new_state, events):
        return new_state, events

    for action in actions:
        actor = _find_char(atual, action.char_id)
        if actor is None or not actor.vivo:
            events.append(Event(tipo="acao_invalida", detalhes={"motivo": "personagem_morto", "char": action.char_id}))
            continue

        if _esta_atordoado(actor):
            events.append(Event(tipo="acao_invalida", detalhes={"motivo": "atordoado", "char": actor.id}))
            continue

        skill = _resolve_skill(characters, actor.id, action.skill_id)
        if skill is None:
            events.append(Event(tipo="acao_invalida", detalhes={"motivo": "skill_inexistente", "skill": action.skill_id}))
            continue

        if actor.cooldowns.get(skill.id, 0) > 0:
            events.append(Event(tipo="acao_invalida", detalhes={"motivo": "em_cooldown", "skill": skill.id}))
            continue

        if not _pagar_custo(atual, skill, action):
            events.append(Event(tipo="acao_invalida", detalhes={"motivo": "essencia_insuficiente", "skill": skill.id}))
            continue

        events.append(
            Event(
                tipo="skill_usada",
                detalhes={"jogador": atual.side.value, "char": actor.id, "skill": skill.id, "alvos": list(action.target_ids)},
            )
        )

        targets = _resolver_alvos(skill, actor, action, atual, oponente)
        for target in targets:
            for efeito in skill.efeitos:
                _aplicar_efeito(efeito, source=actor, target=target, source_player=atual, target_player=_find_owner(new_state, target), events=events)

        if skill.cooldown > 0:
            actor.cooldowns[skill.id] = skill.cooldown

    _decrementar_cooldowns(atual)

    if _checar_encerramento(new_state, events):
        return new_state, events

    new_state.turno += 1
    new_state.jogador_atual = PlayerSide.B if new_state.jogador_atual == PlayerSide.A else PlayerSide.A
    novo_atual = new_state.player(new_state.jogador_atual)
    qtd_vivos = sum(1 for c in novo_atual.personagens if c.vivo)
    _gerar_essencias(novo_atual, qtd_vivos, rng)

    events.append(Event(tipo="turno_encerrado", detalhes={"turno": state.turno, "jogador": atual.side.value}))
    return new_state, events


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _find_char(player: PlayerState, char_id: str) -> CharacterState | None:
    return next((c for c in player.personagens if c.id == char_id), None)


def _find_owner(state: MatchState, target: CharacterState) -> PlayerState:
    if any(c is target for c in state.a.personagens):
        return state.a
    return state.b


def _resolve_skill(characters: dict[str, Personagem], char_id: str, skill_id: str) -> Habilidade | None:
    if skill_id == ESQUIVA_SKILL_ID:
        return ESQUIVA
    char = characters.get(char_id)
    if char is None:
        return None
    return next((s for s in char.habilidades if s.id == skill_id), None)


def _esta_atordoado(c: CharacterState) -> bool:
    return any(s.nome == "atordoado" for s in c.status)


def _esta_invulneravel(c: CharacterState) -> bool:
    return any(s.nome == "invulneravel" for s in c.status)


def _reducao_dano_total(c: CharacterState) -> int:
    return sum(s.valor for s in c.status if s.nome == "reducao_dano")


def _buff_dano_total(c: CharacterState) -> int:
    return sum(s.valor for s in c.status if s.nome == "buff_dano")


def _pagar_custo(player: PlayerState, skill: Habilidade, action: Action) -> bool:
    """Valida que o pagamento informado cobre o custo e debita as essências."""
    custo = dict(skill.custo)
    pago = dict(action.paid)

    # Soma do que foi pago precisa cobrir cada custo específico + genérica.
    # Custo específico: precisa pagar exatamente naquela cor.
    # Custo genérico: aceita qualquer cor.
    for tipo, qtd in custo.items():
        if tipo == Essencia.GENERICA:
            continue
        pago_neste_tipo = pago.get(tipo, 0)
        if pago_neste_tipo < qtd:
            return False

    # Total pago vs total custo.
    total_custo = sum(custo.values())
    total_pago = sum(pago.values())
    if total_pago != total_custo:
        return False

    # Verifica disponibilidade no jogador.
    for tipo, qtd in pago.items():
        if tipo == Essencia.GENERICA:
            return False  # GENERICA não é pagável diretamente; jogador escolhe a cor real
        if player.essencias.get(tipo, 0) < qtd:
            return False

    # Debita.
    for tipo, qtd in pago.items():
        player.essencias[tipo] -= qtd
    return True


def _resolver_alvos(
    skill: Habilidade,
    actor: CharacterState,
    action: Action,
    atual: PlayerState,
    oponente: PlayerState,
) -> list[CharacterState]:
    if skill.alvo == Alvo.SI_MESMO:
        return [actor]
    if skill.alvo == Alvo.TODOS_INIMIGOS:
        return [c for c in oponente.personagens if c.vivo]
    if skill.alvo == Alvo.TODOS_ALIADOS:
        return [c for c in atual.personagens if c.vivo]
    if skill.alvo == Alvo.INIMIGO_UNICO:
        if not action.target_ids:
            return []
        target = _find_char(oponente, action.target_ids[0])
        return [target] if target and target.vivo else []
    if skill.alvo == Alvo.ALIADO_UNICO:
        if not action.target_ids:
            return []
        target = _find_char(atual, action.target_ids[0])
        return [target] if target and target.vivo else []
    return []


def _aplicar_efeito(
    efeito: Efeito,
    source: CharacterState,
    target: CharacterState,
    source_player: PlayerState,
    target_player: PlayerState,
    events: list[Event],
) -> None:
    if efeito.tipo == TipoEfeito.DANO:
        if _esta_invulneravel(target) and not efeito.verdadeiro:
            return
        dano = efeito.valor + _buff_dano_total(source)
        if not efeito.perfurante:
            dano = max(0, dano - _reducao_dano_total(target))
            if target.escudo > 0:
                absorvido = min(target.escudo, dano)
                target.escudo -= absorvido
                dano -= absorvido
        target.hp = max(0, target.hp - dano)
        events.append(
            Event(
                tipo="dano",
                detalhes={"de": source.id, "para": target.id, "valor": dano},
            )
        )
        if not target.vivo:
            events.append(Event(tipo="personagem_derrotado", detalhes={"char": target.id}))
        return

    if efeito.tipo == TipoEfeito.CURA:
        antes = target.hp
        target.hp = min(target.hp_max, target.hp + efeito.valor)
        events.append(
            Event(tipo="cura", detalhes={"para": target.id, "valor": target.hp - antes})
        )
        return

    if efeito.tipo == TipoEfeito.INVULNERAVEL:
        target.status.append(StatusAtivo(nome="invulneravel", duracao=efeito.duracao))
        events.append(Event(tipo="status_aplicado", detalhes={"char": target.id, "status": "invulneravel", "duracao": efeito.duracao}))
        return

    if efeito.tipo == TipoEfeito.REDUCAO_DANO:
        target.status.append(StatusAtivo(nome="reducao_dano", duracao=efeito.duracao, valor=efeito.valor))
        events.append(Event(tipo="status_aplicado", detalhes={"char": target.id, "status": "reducao_dano", "duracao": efeito.duracao, "valor": efeito.valor}))
        return

    if efeito.tipo == TipoEfeito.BUFF_DANO:
        target.status.append(StatusAtivo(nome="buff_dano", duracao=efeito.duracao, valor=efeito.valor))
        events.append(Event(tipo="status_aplicado", detalhes={"char": target.id, "status": "buff_dano", "duracao": efeito.duracao, "valor": efeito.valor}))
        return

    if efeito.tipo == TipoEfeito.ESCUDO_DESTRUTIVEL:
        target.escudo += efeito.valor
        events.append(Event(tipo="status_aplicado", detalhes={"char": target.id, "status": "escudo", "valor": efeito.valor}))
        return

    if efeito.tipo == TipoEfeito.STATUS:
        if efeito.status is None:
            return
        target.status.append(
            StatusAtivo(nome=efeito.status, duracao=efeito.duracao, valor=efeito.valor, fonte=source.id)
        )
        events.append(Event(tipo="status_aplicado", detalhes={"char": target.id, "status": efeito.status, "duracao": efeito.duracao, "valor": efeito.valor}))
        return

    if efeito.tipo == TipoEfeito.DRENO_ESSENCIA:
        # Drena N essências aleatórias do jogador alvo.
        rng = SeededRng(hash((source.id, target.id, len(events))) & 0x7FFFFFFF)
        for _ in range(efeito.valor):
            disponiveis = [e for e in ESSENCIAS_SORTEAVEIS if target_player.essencias.get(e, 0) > 0]
            if not disponiveis:
                break
            escolhida_str = rng.choice([e.value for e in disponiveis])
            escolhida = Essencia(escolhida_str)
            target_player.essencias[escolhida] -= 1
            events.append(Event(tipo="essencia_drenada", detalhes={"de": target_player.side.value, "tipo": escolhida.value}))
        return

    if efeito.tipo == TipoEfeito.REMOVE_AFLICOES:
        aflicoes = {"sangramento", "veneno", "atordoado", "silenciado", "desarmado", "drenado", "marcado", "vulneravel"}
        target.status = [s for s in target.status if s.nome not in aflicoes]
        events.append(Event(tipo="status_expirou", detalhes={"char": target.id, "removido": "aflicoes"}))
        return


def _tick_status(player: PlayerState, events: list[Event]) -> None:
    """Aplica DoTs e decrementa duração. Status com duração 0 são removidos."""
    for char in player.personagens:
        if not char.vivo:
            continue

        # 1. DoTs aplicam dano antes de decrementar duração.
        for s in char.status:
            if s.nome == "veneno" and s.valor > 0:
                char.hp = max(0, char.hp - s.valor)
                events.append(Event(tipo="dano", detalhes={"de": "veneno", "para": char.id, "valor": s.valor}))
            elif s.nome == "regeneracao" and s.valor > 0:
                antes = char.hp
                char.hp = min(char.hp_max, char.hp + s.valor)
                events.append(Event(tipo="cura", detalhes={"para": char.id, "valor": char.hp - antes}))

        if not char.vivo:
            events.append(Event(tipo="personagem_derrotado", detalhes={"char": char.id}))

        # 2. Decrementa duração; remove expirados.
        sobreviventes: list[StatusAtivo] = []
        for s in char.status:
            s.duracao -= 1
            if s.duracao > 0:
                sobreviventes.append(s)
            else:
                events.append(Event(tipo="status_expirou", detalhes={"char": char.id, "status": s.nome}))
        char.status = sobreviventes


def _decrementar_cooldowns(player: PlayerState) -> None:
    for char in player.personagens:
        for skill_id in list(char.cooldowns.keys()):
            char.cooldowns[skill_id] = max(0, char.cooldowns[skill_id] - 1)
            if char.cooldowns[skill_id] == 0:
                del char.cooldowns[skill_id]


def _gerar_essencias(player: PlayerState, qtd: int, rng: SeededRng) -> None:
    for _ in range(qtd):
        escolhida_str = rng.choice([e.value for e in ESSENCIAS_SORTEAVEIS])
        escolhida = Essencia(escolhida_str)
        player.essencias[escolhida] = player.essencias.get(escolhida, 0) + 1


def _checar_encerramento(state: MatchState, events: list[Event]) -> bool:
    if state.a.derrotado and state.b.derrotado:
        state.encerrado = True
        state.vencedor = None  # empate raro
        events.append(Event(tipo="partida_encerrada", detalhes={"vencedor": None}))
        return True
    if state.a.derrotado:
        state.encerrado = True
        state.vencedor = PlayerSide.B
        events.append(Event(tipo="partida_encerrada", detalhes={"vencedor": "B"}))
        return True
    if state.b.derrotado:
        state.encerrado = True
        state.vencedor = PlayerSide.A
        events.append(Event(tipo="partida_encerrada", detalhes={"vencedor": "A"}))
        return True
    return False
