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

  // ── skills (starter trio) ────────────────────────────────────────────
  "skill.spear.name": "Lança Mortal",
  "skill.charge.name": "Investida Heroica",
  "skill.divine_armor.name": "Armadura Divina",
  "skill.aegis.name": "Égide de Atena",
  "skill.smite.name": "Golpe da Coruja",
  "skill.wisdom.name": "Sabedoria da Cidade",
  "skill.wraps.name": "Bandagens Sufocantes",
  "skill.scales.name": "Balança de Anúbis",
  "skill.gateway.name": "Portal do Pós-Vida",
};
