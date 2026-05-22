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
  "nav.help": "Help",
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
  "common.sideA": "Side A",
  "common.sideB": "Side B",
  "common.dash": "—",

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
  "characters.noResults": "No characters match those filters.",
  "characters.searchPlaceholder": "Search by name, mythology, archetype",
  "characters.filter.mythology": "Mythology",
  "characters.filter.archetype": "Archetype",
  "characters.filter.clearAll": "Clear filters",
  // Archetype labels (engine canonical names — used as i18n keys here)
  "characters.archetype.damage_dealer": "damage dealer",
  "characters.archetype.healer": "healer",
  "characters.archetype.tank": "tank",
  "characters.archetype.stunner": "stunner",
  "characters.archetype.drainer": "drainer",
  "characters.archetype.trickster": "trickster",
  "characters.archetype.support": "support",
  "characters.archetype.leader": "leader",
  // Mythology labels (lowercased ids; YAML carries title-case but we
  // i18n-lookup against the lowercased form to keep keys stable).
  "characters.mythology.greek": "Greek",
  "characters.mythology.norse": "Norse",
  "characters.mythology.egyptian": "Egyptian",
  "characters.mythology.chinese": "Chinese",
  "characters.mythology.japanese": "Japanese",
  "characters.mythology.aztec": "Aztec",
  "characters.mythology.african": "African",
  "characters.mythology.mesopotamian": "Mesopotamian",
  "characters.mythology.british": "British",
  "characters.mythology.historical": "Historical",

  // ── skills (every YAML skill, by id) ─────────────────────────────────
  // Greek
  "skill.spear.name": "Deadly Spear",
  "skill.charge.name": "Myrmidon Charge",
  "skill.wrath.name": "Wrath of Peleus",
  "skill.spear_of_wisdom.name": "Spear of Wisdom",
  "skill.counsel.name": "Counsel",
  "skill.aegis.name": "Aegis",
  "skill.unsettling_gaze.name": "Unsettling Gaze",
  "skill.serpent_hiss.name": "Serpent Hiss",
  "skill.petrification.name": "Petrification",
  // Norse
  "skill.mjolnir.name": "Mjolnir",
  "skill.side_thunder.name": "Side Thunder",
  "skill.ragnarok.name": "Ragnarok",
  "skill.golden_lie.name": "Golden Lie",
  "skill.mirror_image.name": "Mirror Image",
  "skill.asgard_deceit.name": "Asgard's Deceit",
  // Egyptian
  "skill.wraps.name": "Choking Wraps",
  "skill.sentence.name": "Sentence",
  "skill.heart_burden.name": "Heart's Burden",
  "skill.mothers_hands.name": "Mother's Hands",
  "skill.protective_wings.name": "Protective Wings",
  "skill.resurgence.name": "Resurgence",
  "skill.royal_decree.name": "Royal Decree",
  "skill.charm.name": "Charm",
  "skill.queen_of_the_nile.name": "Queen of the Nile",
  // Chinese
  "skill.crescent_staff.name": "Crescent Staff",
  "skill.hair_clones.name": "Hair Clones",
  "skill.monkey_king.name": "Monkey King",
  "skill.hidden_sword.name": "Hidden Sword",
  "skill.disguise.name": "Disguise",
  "skill.family_honor.name": "Family Honor",
  // Japanese
  "skill.solar_mirror.name": "Solar Mirror",
  "skill.eternal_morning.name": "Eternal Morning",
  "skill.sacred_cave.name": "Sacred Cave",
  // Aztec
  "skill.whispered_wind.name": "Whispered Wind",
  "skill.sacred_plume.name": "Sacred Plume",
  "skill.sacred_breath.name": "Sacred Breath",
  // African (Akan)
  "skill.spider_thread.name": "Spider Thread",
  "skill.trap.name": "Trap",
  "skill.web_of_lies.name": "Web of Lies",
  // Mesopotamian
  "skill.spear_of_dawn.name": "Spear of Dawn",
  "skill.descent_underworld.name": "Descent to the Underworld",
  "skill.queen_returns.name": "The Queen Returns",
  // Historical
  "skill.sacred_sword.name": "Sacred Sword",
  "skill.standard_raised.name": "Standard Raised",
  "skill.vow_of_orleans.name": "Vow of Orléans",
  "skill.excalibur.name": "Excalibur",
  "skill.inspire_knights.name": "Inspire Knights",
  "skill.round_table.name": "Round Table",

  // ── arenas page ──────────────────────────────────────────────────────
  "arenas.title": "Arenas",
  "arenas.loading": "Loading arenas…",
  "arenas.failed": "Failed: {{error}}",
  "arenas.noModifiers": "No modifiers",
  "arenas.modifierCount": "{{count}} modifier(s)",

  // ── matches page ─────────────────────────────────────────────────────
  "matches.title": "Recent matches",
  "matches.failed": "Failed: {{error}}",
  "matches.empty": "No matches yet — finish one and it'll show up here.",
  "matches.col.when": "When",
  "matches.col.arena": "Arena",
  "matches.col.sideA": "Side A",
  "matches.col.sideB": "Side B",
  "matches.col.winner": "Winner",
  "matches.col.outcome": "Outcome",
  "matches.col.turns": "Turns",
  "matches.col.elo": "ELO Δ",
  "matches.draw": "draw",
  "matches.outcome.win": "Win",
  "matches.outcome.loss": "Loss",
  "matches.outcome.draw": "Draw",
  "matches.summary.played": "Played",
  "matches.summary.wins": "Wins",
  "matches.summary.losses": "Losses",
  "matches.summary.draws": "Draws",
  "matches.summary.netElo": "Net ELO",
  "matches.summary.winRate": "{{rate}}% win rate",

  // ── draft page ───────────────────────────────────────────────────────
  "draft.devTitle": "Ranked Draft (dev mode)",
  "draft.devTagline":
    "Drives both sides locally. For multiplayer head to {{matchmakingLink}}.",
  "draft.matchmakingLink": "Matchmaking",
  "draft.arenaLabel": "Arena:",
  "draft.startDraft": "Start draft",
  "draft.connecting": "Connecting to draft…",
  "draft.catalogFailed": "Catalog failed to load.",
  "draft.title": "Draft",
  "draft.youAreSide": "— you are side {{side}}",
  "draft.arenaIs": "Arena {{arena}}",
  "draft.phaseLabel": "Phase: {{phase}}",
  "draft.phase.ban": "BAN",
  "draft.phase.pick": "PICK",
  "draft.phase.confirm": "CONFIRM",
  "draft.phase.done": "DONE",
  "draft.phase.cancelled": "CANCELLED",
  "draft.nowActing": "Now acting:",
  "draft.sideX": "side {{side}}",
  "draft.youSuffix": "(you)",
  "draft.pool": "Pool",
  "draft.lockedHint": "(locked picks are greyed out)",
  "draft.banShort": "Ban: {{value}}",
  "draft.picksShort": "Picks: {{value}}",
  "draft.complete": "Draft complete. Starting match…",
  "draft.notAuth": "Not authenticated.",
  "draft.wsError": "WebSocket error.",

  // ── status effects (label + description for badge tooltip) ──────────
  // Keys mirror server-side status names verbatim. Missing entries fall
  // back to a humanised version of the id (`disarm` → "disarm").
  "status.poison.label": "poison",
  "status.poison.description": "Deals damage each turn based on value.",
  "status.bleed.label": "bleed",
  "status.bleed.description": "Deals damage each turn. Removed when healed.",
  "status.stun.label": "stun",
  "status.stun.description": "Cannot act this turn.",
  "status.silence.label": "silence",
  "status.silence.description": "Cannot use non-physical skills.",
  "status.disarm.label": "disarm",
  "status.disarm.description": "Cannot use physical skills.",
  "status.stealth.label": "stealth",
  "status.stealth.description": "Cannot be targeted by single-target skills.",
  "status.reflective.label": "reflective",
  "status.reflective.description": "Reflects a portion of damage back to the attacker.",
  "status.invulnerable.label": "invulnerable",
  "status.invulnerable.description": "Immune to all damage and harmful effects.",
  "status.damage_reduction.label": "damage reduction",
  "status.damage_reduction.description": "Incoming damage is reduced by the stack value.",
  "status.damage_buff.label": "damage buff",
  "status.damage_buff.description": "Outgoing damage is increased by the stack value.",
  "status.regen.label": "regen",
  "status.regen.description": "Recovers HP at the start of each turn.",
  "status.vulnerable.label": "vulnerable",
  "status.vulnerable.description": "Cannot resist new negative status effects.",
  "status.marked.label": "marked",
  "status.marked.description": "Takes bonus damage from all sources.",
  "status.drained.label": "drained",
  "status.drained.description": "Loses essence each turn.",
  "status.shield.label": "shield",
  "status.shield.description":
    "Absorbs incoming damage before HP is reduced. Lasts until depleted.",
  "status.fallback.description": "Active status effect.",
  "status.duration.infinite": "∞",
  "status.duration.label": "Duration:",
  "status.duration.turns": "turns",
  "status.duration.turn": "turn",

  // ── help page ────────────────────────────────────────────────────────
  "help.title": "How to play",
  "help.tagline":
    "Quick reference for new players. Skim it before your first ranked match.",
  "help.toc.title": "Sections",
  "help.toc.match": "Match",
  "help.toc.essences": "Essences",
  "help.toc.skills": "Skills",
  "help.toc.statuses": "Statuses",
  "help.match.title": "How a match works",
  "help.match.format":
    "Two players each control a team of three mythological figures. Sides take alternating turns until one team's characters are all knocked out.",
  "help.match.flow":
    "Each turn: status effects tick, your active side's cooldowns decrement, then you queue actions (one per character), and finally Confirm. The opponent plays next.",
  "help.match.timer":
    "You have 60 seconds per turn. If you don't confirm, the server auto-resolves with whatever you've queued.",
  "help.match.win":
    "First side to reduce all three opponents to 0 HP wins. Long matches (60+ turns) decide on remaining HP.",
  "help.essences.title": "Essences (energy)",
  "help.essences.intro":
    "Skills cost essences. There are four colored types plus a wildcard generic slot:",
  "help.essences.vigor": "Vigor",
  "help.essences.vigor.desc": "physical force, melee combat",
  "help.essences.spirit": "Spirit",
  "help.essences.spirit.desc": "arcane magic, elemental control",
  "help.essences.mind": "Mind",
  "help.essences.mind.desc": "illusion, manipulation, knowledge",
  "help.essences.blood": "Blood",
  "help.essences.blood.desc": "divine lineage, transformation",
  "help.essences.generic": "Generic",
  "help.essences.generic.desc":
    "any color satisfies a generic slot — you pick what to spend",
  "help.essences.generation":
    "At the start of your turn you roll one random essence per alive character (up to 3). Unused essences stack between turns.",
  "help.skills.title": "Skills",
  "help.skills.intro":
    "Each character has three skills plus a universal Dodge. Click a skill to start the action; pick a target on the board to confirm.",
  "help.skills.cost":
    "Cost: shown as colored dots next to the skill. You must have matching essences to pay it.",
  "help.skills.cooldown":
    "Cooldown: number of turns before the skill is usable again. Dodge resets after 4 turns.",
  "help.skills.targets":
    "Targets: a skill aims at a single enemy, all enemies, a single ally, all allies, or itself — the UI highlights only the legal targets.",
  "help.skills.queue":
    "Queue up to one action per character, reorder if needed, then press Confirm. Actions resolve in the order you queued them.",
  "help.statuses.title": "Status effects",
  "help.statuses.intro":
    "Statuses last for a number of turns and modify what a character can do or how much damage they deal or take.",
  // ── error codes (HTTP) ───────────────────────────────────────────────
  "error.match.bad_team_size": "Each team must have exactly 3 characters.",
  "error.match.unknown_id": "Unknown character or arena id.",
  "error.match.not_found": "Match not found.",
  "error.character.not_found": "Character not found.",
  "error.arena.not_found": "Arena not found.",
  "error.draft.not_found": "Draft not found.",
  "error.draft.error": "Couldn't process that draft action.",
  "error.draft.bad_phase": "The draft isn't ready for that yet.",

  // ── error codes (auth) ───────────────────────────────────────────────
  "error.auth.google.redirect_uri_missing":
    "Google sign-in isn't fully configured (redirect URI missing).",
  "error.auth.google.not_configured":
    "Google sign-in isn't enabled on this server.",
  "error.auth.google.no_subject":
    "Google didn't return a verified account; please try again.",
  "error.auth.apple.not_configured":
    "Apple sign-in isn't enabled on this server.",
  "error.auth.apple.missing_code": "Apple didn't return an authorization code.",
  "error.auth.apple.token_exchange_failed":
    "Couldn't reach Apple's token endpoint. Try again in a moment.",
  "error.auth.apple.no_id_token":
    "Apple didn't return an identity token; please try again.",
  "error.auth.apple.id_token_invalid":
    "Apple's identity token failed verification.",
  "error.auth.dev_token.disabled":
    "The dev token endpoint is disabled in this environment.",
};
