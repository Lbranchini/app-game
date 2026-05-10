/* eslint-disable */
/**
 * Portuguese (Brazil) translation map. Mirrors every key in `en.ts` —
 * any missing key falls back to English at runtime via `translate()`.
 */

export const ptBR: Record<string, string> = {
  // ── nav ──────────────────────────────────────────────────────────────
  "nav.brand": "Ágora dos Mitos",
  "nav.characters": "Personagens",
  "nav.arenas": "Arenas",
  "nav.play": "Jogar",
  "nav.draft": "Draft (dev)",
  "nav.battle": "Batalha (dev)",
  "nav.matches": "Partidas",
  "nav.signOut": "Sair",
  "nav.elo": "ELO {{elo}}",

  // ── common ───────────────────────────────────────────────────────────
  "common.cancel": "Cancelar",
  "common.retry": "Tentar de novo",
  "common.tryAgain": "Tentar de novo",
  "common.reload": "Recarregar",
  "common.loading": "Carregando…",
  "common.you": "Você",
  "common.opponent": "Oponente",
  "common.empty": "vazio",
  "common.free": "grátis",
  "common.sideA": "Lado A",
  "common.sideB": "Lado B",
  "common.dash": "—",

  // ── login ────────────────────────────────────────────────────────────
  "login.tagline": "Entre para acessar a Ágora.",
  "login.continueWithGoogle": "Continuar com o Google",
  "login.continueWithApple": "Continuar com a Apple",
  "login.localDev": "Desenvolvimento local:",
  "login.devToken": "Token dev (local apenas)",

  // ── matchmaking ──────────────────────────────────────────────────────
  "matchmaking.title": "Fila ranqueada",
  "matchmaking.tagline":
    "Entre na fila. O servidor pareia você com o próximo jogador e leva os dois pro draft.",
  "matchmaking.joinQueue": "Entrar na fila",
  "matchmaking.leaveQueue": "Sair da fila",
  "matchmaking.tip": "Clique abaixo para começar a procurar um oponente.",
  "matchmaking.searching": "Procurando oponente…",
  "matchmaking.tipBand": "Dica: a faixa de ELO se alarga com o passar do tempo.",
  "matchmaking.matchFound": "Partida encontrada",
  "matchmaking.routing": "Levando você para o draft…",
  "matchmaking.notAuth": "Não autenticado.",
  "matchmaking.wsError": "Erro no WebSocket.",

  // ── battle ───────────────────────────────────────────────────────────
  "battle.demoTitle": "Batalha (demo)",
  "battle.demoTagline": "Inicia uma partida entre {{teamA}} e {{teamB}} no Olimpo.",
  "battle.startMatch": "Iniciar partida",
  "battle.startNewMatch": "Iniciar nova partida",
  "battle.couldntLoad": "Não foi possível carregar a partida",
  "battle.backToMatchmaking": "Voltar pra fila",
  "battle.loadingMatch": "Carregando partida {{id}}…",
  "battle.yourTurn": "Seu turno · {{seconds}}s",
  "battle.opponentTurn": "Turno do oponente · {{seconds}}s",
  "battle.confirmTurn": "Confirmar turno",
  "battle.opponentTurnLabel": "Turno do oponente",
  "battle.clear": "Limpar",
  "battle.matchFinished": "Partida encerrada",
  "battle.draw": "Empate",
  "battle.sideAWins": "Lado A venceu",
  "battle.sideBWins": "Lado B venceu",
  "battle.winner": "vencedor",
  "battle.essencePool": "Reserva de essências",
  "battle.actionsQueued": "{{count}}/3 enfileiradas",
  "battle.noActionsQueued": "nenhuma ação enfileirada",
  "battle.opponentDisconnected":
    "Oponente desconectou — derrota automática em {{seconds}}s",
  "battle.match": "partida",
  "battle.arena": "arena",
  "battle.eventLog": "Eventos ({{count}})",
  "battle.youTeam": "Você · Lado {{side}}",
  "battle.opponentTeam": "Oponente · Lado {{side}}",
  "battle.unmute": "Reativar som",
  "battle.mute": "Silenciar",
  "battle.soundsOn": "Som ligado",
  "battle.soundsOff": "Som desligado",
  "battle.targetEnemy": "→ Clique num oponente para usar",
  "battle.targetAllEnemies": "→ Clique em qualquer oponente para acertar todos",
  "battle.targetAlly": "→ Clique num aliado para usar",
  "battle.targetSelf": "→ Aplica em si",
  "battle.dmgDealt": "dano causado",
  "battle.dmgTaken": "dano sofrido",
  "battle.healing": "cura",
  "battle.knockedOut": "KO",
  "battle.cooldown": "CD {{turns}}",
  "battle.stunned": "atordoado",
  "battle.queued": "enfileirado",
  "battle.down": "abatido",
  "battle.empty": "vazio",

  // ── reconnect overlay ────────────────────────────────────────────────
  "reconnect.connectionLost": "Conexão perdida",
  "reconnect.connectionLostBody":
    "Não conseguimos restaurar a conexão com o servidor. A partida pode ter sido encerrada com derrota.",
  "reconnect.reconnecting": "Reconectando…",
  "reconnect.attempt": "tentativa {{current}} / {{max}}",
  "reconnect.nextIn": "próxima em {{seconds}}s",
  "reconnect.retryNow": "Tentar agora",

  // ── error boundary ───────────────────────────────────────────────────
  "error.somethingBroke": "Algo quebrou",
  "error.boundaryBody":
    "A página encontrou um erro inesperado. Já registramos o stack trace; tente recarregar ou voltar para Personagens.",
  "error.backToCharacters": "Voltar para Personagens",
  // ── error codes (mensagens emitidas pelo servidor) ───────────────────
  "error.match.unknown_frame": "Não consegui entender essa mensagem — tente de novo.",
  "error.match.bad_action": "Essa ação parece inválida.",
  "error.match.match_over": "A partida já foi encerrada.",
  "error.match.not_your_turn": "Calma — é o turno do oponente.",

  // ── characters page ──────────────────────────────────────────────────
  "characters.title": "Roster",
  "characters.unlocked": "Desbloqueados",
  "characters.locked": "Bloqueados",
  "characters.unlockedCount": "{{unlocked}}/{{total}} desbloqueados",
  "characters.loading": "Carregando personagens…",
  "characters.failed": "Falhou: {{error}}",
  "characters.lockedSubtitle": "HP {{hp}} • {{archetype}} · bloqueado",
  "characters.openSubtitle": "HP {{hp}} • {{archetype}}",
  "characters.noUnlockRule": "Nenhuma regra de desbloqueio cadastrada ainda.",
  "characters.noResults": "Nenhum personagem corresponde a esses filtros.",
  "characters.searchPlaceholder": "Buscar por nome, mitologia ou arquétipo",
  "characters.filter.mythology": "Mitologia",
  "characters.filter.archetype": "Arquétipo",
  "characters.filter.clearAll": "Limpar filtros",
  // Arquétipos
  "characters.archetype.damage_dealer": "atacante",
  "characters.archetype.healer": "curandeiro",
  "characters.archetype.tank": "tanque",
  "characters.archetype.stunner": "atordoador",
  "characters.archetype.drainer": "drenador",
  "characters.archetype.trickster": "trapaceiro",
  "characters.archetype.support": "suporte",
  "characters.archetype.leader": "líder",
  // Mitologias
  "characters.mythology.greek": "Grega",
  "characters.mythology.norse": "Nórdica",
  "characters.mythology.egyptian": "Egípcia",
  "characters.mythology.chinese": "Chinesa",
  "characters.mythology.japanese": "Japonesa",
  "characters.mythology.aztec": "Asteca",
  "characters.mythology.african": "Africana",
  "characters.mythology.mesopotamian": "Mesopotâmica",
  "characters.mythology.british": "Britânica",
  "characters.mythology.historical": "Histórica",

  // ── skills (todos os ids do YAML) ────────────────────────────────────
  // Gregos
  "skill.spear.name": "Lança Mortal",
  "skill.charge.name": "Investida Mirmídone",
  "skill.wrath.name": "Ira de Peleu",
  "skill.spear_of_wisdom.name": "Lança da Sabedoria",
  "skill.counsel.name": "Conselho",
  "skill.aegis.name": "Égide",
  "skill.unsettling_gaze.name": "Olhar Inquietante",
  "skill.serpent_hiss.name": "Sibilo das Serpentes",
  "skill.petrification.name": "Petrificação",
  // Nórdicos
  "skill.mjolnir.name": "Mjölnir",
  "skill.side_thunder.name": "Trovão Lateral",
  "skill.ragnarok.name": "Ragnarök",
  "skill.golden_lie.name": "Mentira Dourada",
  "skill.mirror_image.name": "Imagem Espelhada",
  "skill.asgard_deceit.name": "Trapaça de Asgard",
  // Egípcios
  "skill.wraps.name": "Bandagens Sufocantes",
  "skill.sentence.name": "Sentença",
  "skill.heart_burden.name": "Peso do Coração",
  "skill.mothers_hands.name": "Mãos da Mãe",
  "skill.protective_wings.name": "Asas Protetoras",
  "skill.resurgence.name": "Ressurgimento",
  "skill.royal_decree.name": "Decreto Real",
  "skill.charm.name": "Encanto",
  "skill.queen_of_the_nile.name": "Rainha do Nilo",
  // Chineses
  "skill.crescent_staff.name": "Cajado Crescente",
  "skill.hair_clones.name": "Clones de Cabelo",
  "skill.monkey_king.name": "Rei dos Macacos",
  "skill.hidden_sword.name": "Espada Oculta",
  "skill.disguise.name": "Disfarce",
  "skill.family_honor.name": "Honra da Família",
  // Japoneses
  "skill.solar_mirror.name": "Espelho Solar",
  "skill.eternal_morning.name": "Manhã Eterna",
  "skill.sacred_cave.name": "Caverna Sagrada",
  // Astecas
  "skill.whispered_wind.name": "Vento Sussurrado",
  "skill.sacred_plume.name": "Plumagem Sagrada",
  "skill.sacred_breath.name": "Sopro Sagrado",
  // Africano (Akan)
  "skill.spider_thread.name": "Fio da Aranha",
  "skill.trap.name": "Armadilha",
  "skill.web_of_lies.name": "Teia de Mentiras",
  // Mesopotâmicos
  "skill.spear_of_dawn.name": "Lança da Aurora",
  "skill.descent_underworld.name": "Descida ao Submundo",
  "skill.queen_returns.name": "O Retorno da Rainha",
  // Históricos
  "skill.sacred_sword.name": "Espada Sagrada",
  "skill.standard_raised.name": "Estandarte Erguido",
  "skill.vow_of_orleans.name": "Voto de Orléans",
  "skill.excalibur.name": "Excálibur",
  "skill.inspire_knights.name": "Inspirar Cavaleiros",
  "skill.round_table.name": "Távola Redonda",

  // ── arenas page ──────────────────────────────────────────────────────
  "arenas.title": "Arenas",
  "arenas.loading": "Carregando arenas…",
  "arenas.failed": "Falhou: {{error}}",
  "arenas.noModifiers": "Sem modificadores",
  "arenas.modifierCount": "{{count}} modificador(es)",

  // ── matches page ─────────────────────────────────────────────────────
  "matches.title": "Partidas recentes",
  "matches.failed": "Falhou: {{error}}",
  "matches.empty": "Nenhuma partida ainda — termine uma e ela aparece aqui.",
  "matches.col.when": "Quando",
  "matches.col.arena": "Arena",
  "matches.col.sideA": "Lado A",
  "matches.col.sideB": "Lado B",
  "matches.col.winner": "Vencedor",
  "matches.col.turns": "Turnos",
  "matches.col.elo": "ELO Δ",
  "matches.draw": "empate",

  // ── draft page ───────────────────────────────────────────────────────
  "draft.devTitle": "Draft Ranqueado (modo dev)",
  "draft.devTagline":
    "Controla os dois lados localmente. Para multiplayer, vá em {{matchmakingLink}}.",
  "draft.matchmakingLink": "Matchmaking",
  "draft.arenaLabel": "Arena:",
  "draft.startDraft": "Iniciar draft",
  "draft.connecting": "Conectando ao draft…",
  "draft.catalogFailed": "Falha ao carregar o catálogo.",
  "draft.title": "Draft",
  "draft.youAreSide": "— você é o lado {{side}}",
  "draft.arenaIs": "Arena {{arena}}",
  "draft.phaseLabel": "Fase: {{phase}}",
  "draft.phase.ban": "BANIR",
  "draft.phase.pick": "ESCOLHER",
  "draft.phase.confirm": "CONFIRMAR",
  "draft.phase.done": "PRONTO",
  "draft.phase.cancelled": "CANCELADO",
  "draft.nowActing": "Agindo agora:",
  "draft.sideX": "lado {{side}}",
  "draft.youSuffix": "(você)",
  "draft.pool": "Pool",
  "draft.lockedHint": "(picks bloqueados ficam apagados)",
  "draft.banShort": "Banimento: {{value}}",
  "draft.picksShort": "Picks: {{value}}",
  "draft.complete": "Draft completo. Iniciando partida…",
  "draft.notAuth": "Não autenticado.",
  "draft.wsError": "Erro no WebSocket.",

  // ── status effects (label + descrição da bolha do badge) ────────────
  "status.poison.label": "veneno",
  "status.poison.description": "Causa dano a cada turno baseado no valor.",
  "status.bleed.label": "sangramento",
  "status.bleed.description": "Causa dano a cada turno. Removido ao curar.",
  "status.stun.label": "atordoado",
  "status.stun.description": "Não pode agir neste turno.",
  "status.silence.label": "silenciado",
  "status.silence.description": "Não pode usar habilidades não-físicas.",
  "status.disarm.label": "desarmado",
  "status.disarm.description": "Não pode usar habilidades físicas.",
  "status.stealth.label": "furtivo",
  "status.stealth.description":
    "Não pode ser alvo de habilidades de alvo único.",
  "status.reflective.label": "reflexivo",
  "status.reflective.description":
    "Reflete uma parte do dano de volta para o atacante.",
  "status.invulnerable.label": "invulnerável",
  "status.invulnerable.description":
    "Imune a todo dano e efeitos negativos.",
  "status.damage_reduction.label": "redução de dano",
  "status.damage_reduction.description":
    "Dano recebido é reduzido pelo valor da pilha.",
  "status.damage_buff.label": "dano aumentado",
  "status.damage_buff.description":
    "Dano causado é aumentado pelo valor da pilha.",
  "status.regen.label": "regeneração",
  "status.regen.description": "Recupera HP no início de cada turno.",
  "status.vulnerable.label": "vulnerável",
  "status.vulnerable.description":
    "Não pode resistir a novos efeitos de status negativos.",
  "status.marked.label": "marcado",
  "status.marked.description":
    "Recebe dano extra de todas as fontes.",
  "status.drained.label": "drenado",
  "status.drained.description": "Perde uma essência a cada turno.",
  "status.shield.label": "escudo",
  "status.shield.description":
    "Absorve dano antes do HP. Dura até ser quebrado.",
  "status.fallback.description": "Efeito de status ativo.",
  "status.duration.infinite": "∞",
  "status.duration.label": "Duração:",
  "status.duration.turns": "turnos",
  "status.duration.turn": "turno",

  // ── error codes (HTTP) ───────────────────────────────────────────────
  "error.match.bad_team_size": "Cada time precisa ter exatamente 3 personagens.",
  "error.match.unknown_id": "ID de personagem ou arena desconhecido.",
  "error.match.not_found": "Partida não encontrada.",
  "error.character.not_found": "Personagem não encontrado.",
  "error.arena.not_found": "Arena não encontrada.",
  "error.draft.not_found": "Draft não encontrado.",
  "error.draft.error": "Não consegui processar essa ação no draft.",
  "error.draft.bad_phase": "O draft ainda não está pronto pra isso.",

  // ── error codes (auth) ───────────────────────────────────────────────
  "error.auth.google.redirect_uri_missing":
    "Login com Google não está configurado (redirect URI ausente).",
  "error.auth.google.not_configured":
    "Login com Google não está habilitado neste servidor.",
  "error.auth.google.no_subject":
    "O Google não retornou uma conta verificada; tente novamente.",
  "error.auth.apple.not_configured":
    "Login com Apple não está habilitado neste servidor.",
  "error.auth.apple.missing_code":
    "A Apple não retornou um código de autorização.",
  "error.auth.apple.token_exchange_failed":
    "Não consegui contatar o servidor da Apple. Tente em alguns segundos.",
  "error.auth.apple.no_id_token":
    "A Apple não retornou um token de identidade; tente novamente.",
  "error.auth.apple.id_token_invalid":
    "O token da Apple falhou na verificação.",
  "error.auth.dev_token.disabled":
    "O endpoint de token dev está desabilitado neste ambiente.",
};
