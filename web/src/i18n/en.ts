/* eslint-disable */
/**
 * English translation map (master). Keys are dot-namespaced by surface:
 *   nav.*           top-level navigation
 *   common.*        generic words reused all over (cancel, retry, ...)
 *   login.*         /login page
 *   matchmaking.*   /matchmaking page
 *   battle.*        /battle page (HUD, banners, overlays)
 *   characters.*    /characters page
 *   error.*         error UI / boundary
 *   skill.<id>.name|description (a small starter set; rest fall back to YAML English)
 */

export const en: Record<string, string> = {
  // ── nav ──────────────────────────────────────────────────────────────
  "nav.brand": "Agora of Myths",
  "nav.characters": "Characters",
  "nav.arenas": "Arenas",
  "nav.play": "Play",
  "nav.draft": "Draft (dev)",
  "nav.battle": "Battle (dev)",
  "nav.matches": "Matches",
  "nav.signOut": "Sign out",
  "nav.elo": "ELO {{elo}}",

  // ── common ───────────────────────────────────────────────────────────
  "common.cancel": "Cancel",
  "common.retry": "Retry",
  "common.tryAgain": "Try again",
  "common.reload": "Reload",
  "common.loading": "Loading…",
  "common.you": "You",
  "common.opponent": "Opponent",
  "common.empty": "empty",
  "common.free": "free",

  // ── login ────────────────────────────────────────────────────────────
  "login.tagline": "Sign in to enter the Agora.",
  "login.continueWithGoogle": "Continue with Google",
  "login.continueWithApple": "Continue with Apple",
  "login.localDev": "Local development:",
  "login.devToken": "Dev token (local only)",

  // ── matchmaking ──────────────────────────────────────────────────────
  "matchmaking.title": "Ranked queue",
  "matchmaking.tagline":
    "Join the queue. The server pairs you with the next player and routes you both into a draft.",
  "matchmaking.joinQueue": "Join queue",
  "matchmaking.leaveQueue": "Leave queue",
  "matchmaking.tip": "Click below to start searching for an opponent.",
  "matchmaking.searching": "Searching for opponent…",
  "matchmaking.tipBand": "Tip: matchmaking widens the ELO band over time.",
  "matchmaking.matchFound": "Match found",
  "matchmaking.routing": "Routing you to the draft…",
  "matchmaking.notAuth": "Not authenticated.",
  "matchmaking.wsError": "WebSocket error.",

  // ── battle ───────────────────────────────────────────────────────────
  "battle.demoTitle": "Battle (demo)",
  "battle.demoTagline": "Spawns a match between {{teamA}} and {{teamB}} on Olympus.",
  "battle.startMatch": "Start match",
  "battle.startNewMatch": "Start new match",
  "battle.couldntLoad": "Couldn't load match",
  "battle.backToMatchmaking": "Back to matchmaking",
  "battle.loadingMatch": "Loading match {{id}}…",
  "battle.yourTurn": "Your turn · {{seconds}}s",
  "battle.opponentTurn": "Opponent's turn · {{seconds}}s",
  "battle.confirmTurn": "Confirm turn",
  "battle.opponentTurnLabel": "Opponent's turn",
  "battle.clear": "Clear",
  "battle.matchFinished": "Match finished",
  "battle.draw": "Draw",
  "battle.sideAWins": "Side A wins",
  "battle.sideBWins": "Side B wins",
  "battle.winner": "winner",
  "battle.essencePool": "Essence pool",
  "battle.actionsQueued": "{{count}}/3 queued",
  "battle.noActionsQueued": "no actions queued",
  "battle.opponentDisconnected":
    "Opponent disconnected — auto-forfeit in {{seconds}}s",
  "battle.match": "match",
  "battle.arena": "arena",
  "battle.eventLog": "Event log ({{count}})",
  "battle.youTeam": "You · Side {{side}}",
  "battle.opponentTeam": "Opponent · Side {{side}}",
  "battle.unmute": "Unmute",
  "battle.mute": "Mute",
  "battle.soundsOn": "Sounds on",
  "battle.soundsOff": "Sounds off",
  "battle.targetEnemy": "→ Click an opponent to cast",
  "battle.targetAllEnemies": "→ Click any opponent to hit all enemies",
  "battle.targetAlly": "→ Click an ally to cast",
  "battle.targetSelf": "→ Casts on self",
  "battle.dmgDealt": "dmg dealt",
  "battle.dmgTaken": "dmg taken",
  "battle.healing": "healing",
  "battle.knockedOut": "KO",
  "battle.cooldown": "CD {{turns}}",
  "battle.stunned": "stunned",
  "battle.queued": "queued",
  "battle.down": "down",
  "battle.empty": "empty",

  // ── reconnect overlay ────────────────────────────────────────────────
  "reconnect.connectionLost": "Connection lost",
  "reconnect.connectionLostBody":
    "We couldn't restore the link to the server. The match may have been forfeited.",
  "reconnect.reconnecting": "Reconnecting…",
  "reconnect.attempt": "attempt {{current}} / {{max}}",
  "reconnect.nextIn": "next in {{seconds}}s",
  "reconnect.retryNow": "Retry now",

  // ── error boundary ───────────────────────────────────────────────────
  "error.somethingBroke": "Something broke",
  "error.boundaryBody":
    "The page hit an unexpected error. We've logged the trace; you can try a fresh load or head back to the Characters page.",
  "error.backToCharacters": "Back to Characters",
  // ── error codes (server-emitted, looked up via `error.<code>`) ───────
  "error.match.unknown_frame": "Couldn't parse that message — please retry.",
  "error.match.bad_action": "That action looks malformed.",
  "error.match.match_over": "The match is already finished.",
  "error.match.not_your_turn": "Hold on — it's the opponent's turn.",

  // ── characters page ──────────────────────────────────────────────────
  "characters.title": "Roster",
  "characters.unlocked": "Unlocked",
  "characters.locked": "Locked",
  "characters.unlockedCount": "{{unlocked}}/{{total}} unlocked",
  "characters.loading": "Loading characters…",
  "characters.failed": "Failed: {{error}}",
  "characters.lockedSubtitle": "HP {{hp}} • {{archetype}} · locked",
  "characters.openSubtitle": "HP {{hp}} • {{archetype}}",
  "characters.noUnlockRule": "No unlock rule registered for this character yet.",

  // ── skills (starter trio only — rest fall back to YAML English) ──────
  "skill.spear.name": "Deadly Spear",
  "skill.charge.name": "Heroic Charge",
  "skill.divine_armor.name": "Divine Armor",
  "skill.aegis.name": "Aegis of Athena",
  "skill.smite.name": "Owl's Smite",
  "skill.wisdom.name": "Wisdom of the City",
  "skill.wraps.name": "Choking Wraps",
  "skill.scales.name": "Scales of Anubis",
  "skill.gateway.name": "Gateway to the Afterlife",

  // ── error codes (HTTP) ───────────────────────────────────────────────
  "error.match.bad_team_size": "Each team must have exactly 3 characters.",
  "error.match.unknown_id": "Unknown character or arena id.",
  "error.match.not_found": "Match not found.",
  "error.character.not_found": "Character not found.",
  "error.arena.not_found": "Arena not found.",
  "error.draft.not_found": "Draft not found.",
  "error.draft.error": "Couldn't process that draft action.",
  "error.draft.bad_phase": "The draft isn't ready for that yet.",
};
