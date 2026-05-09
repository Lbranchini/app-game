import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion, useAnimationControls } from "framer-motion";

import { api, auth } from "@/api/client";
import {
  computePayment,
  needsTargetPick,
  subtractPayment,
  type QueuedAction,
} from "@/api/battle";
import { useT } from "@/i18n";
import type { Character, Essence, Skill } from "@/types/api";

// ============================================================================
// TYPES & CONSTANTS
// ============================================================================

interface CharacterState {
  id: string;
  name: string;
  hp: number;
  hp_max: number;
  shield: number;
  shield_source: string | null;
  cooldowns: Record<string, number>;
  statuses: { name: string; duration: number; value: number; source: string | null }[];
}

interface PlayerState {
  id: string;
  side: "A" | "B";
  characters: CharacterState[];
  essences: Partial<Record<Essence, number>>;
}

interface MatchState {
  match_id: string;
  arena_id: string;
  turn: number;
  current_side: "A" | "B";
  a: PlayerState;
  b: PlayerState;
  finished: boolean;
  winner: "A" | "B" | null;
  turn_deadline: string | null;
}

interface MatchEvent {
  kind: string;
  details: Record<string, unknown>;
}

interface FloatingNumber {
  id: number;
  target: string;
  value: number;
  kind: "damage" | "heal";
  tick?: string;
}

const DEMO_TEAM_A = ["achilles", "athena", "anubis"];
const DEMO_TEAM_B = ["thor", "isis", "loki"];

const ESSENCE_STYLE: Record<Essence, { dot: string; chip: string; label: string }> = {
  vigor: { dot: "bg-red-500", chip: "bg-red-500/20 text-red-300 ring-red-500/40", label: "VIG" },
  spirit: { dot: "bg-amber-400", chip: "bg-amber-400/20 text-amber-200 ring-amber-400/40", label: "SPI" },
  mind: { dot: "bg-sky-400", chip: "bg-sky-400/20 text-sky-200 ring-sky-400/40", label: "MND" },
  blood: { dot: "bg-fuchsia-500", chip: "bg-fuchsia-500/20 text-fuchsia-200 ring-fuchsia-500/40", label: "BLD" },
  generic: { dot: "bg-slate-400", chip: "bg-slate-400/20 text-slate-200 ring-slate-400/40", label: "GEN" },
};

const ESSENCE_ORDER: Essence[] = ["vigor", "spirit", "mind", "blood"];
const TURN_TIMER_SECONDS = 60;
const MUTE_KEY = "agora.mute";

// ============================================================================
// AUDIO
// ============================================================================

let audioCtx: AudioContext | null = null;
function getAudioCtx(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (audioCtx) return audioCtx;
  const Ctor =
    typeof AudioContext !== "undefined"
      ? AudioContext
      : (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!Ctor) return null;
  audioCtx = new Ctor();
  return audioCtx;
}

function playBeep(kind: "damage" | "heal"): void {
  if (typeof window === "undefined") return;
  if (window.localStorage.getItem(MUTE_KEY) === "1") return;
  const ctx = getAudioCtx();
  if (!ctx) return;
  if (ctx.state === "suspended") void ctx.resume();
  const t0 = ctx.currentTime;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.connect(gain);
  gain.connect(ctx.destination);
  const profile =
    kind === "damage"
      ? { freq: 220, type: "sawtooth" as OscillatorType, vol: 0.16, dur: 0.12 }
      : { freq: 660, type: "sine" as OscillatorType, vol: 0.12, dur: 0.18 };
  osc.type = profile.type;
  osc.frequency.setValueAtTime(profile.freq, t0);
  gain.gain.setValueAtTime(0, t0);
  gain.gain.linearRampToValueAtTime(profile.vol, t0 + 0.01);
  gain.gain.exponentialRampToValueAtTime(0.001, t0 + profile.dur);
  osc.start(t0);
  osc.stop(t0 + profile.dur + 0.05);
}

// ============================================================================
// MAIN PAGE
// ============================================================================

export function BattlePage() {
  const t = useT();
  const params = useParams<{ matchId?: string }>();
  const [matchId, setMatchId] = useState<string | null>(params.matchId ?? null);
  const [state, setState] = useState<MatchState | null>(null);
  const [events, setEvents] = useState<MatchEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [queue, setQueue] = useState<QueuedAction[]>([]);
  const [floats, setFloats] = useState<FloatingNumber[]>([]);
  const [turnStartedAt, setTurnStartedAt] = useState<number>(() => Date.now());
  const [now, setNow] = useState<number>(() => Date.now());
  const [splashFor, setSplashFor] = useState<string | null>(null);
  const [wsStatus, setWsStatus] = useState<"connecting" | "open" | "closed">("connecting");
  // Which side this socket controls (real matches only). Null in dev hot-
  // seat — the bottom team then follows whoever's acting, like before.
  const [yourSide, setYourSide] = useState<"A" | "B" | null>(null);
  const [opponentOffline, setOpponentOffline] = useState<{ playerId: string; forfeitDeadlineMs: number } | null>(null);
  const [muted, setMuted] = useState<boolean>(() =>
    typeof window === "undefined" ? false : window.localStorage.getItem(MUTE_KEY) === "1"
  );
  const [selectedSkill, setSelectedSkill] = useState<{
    character_id: string;
    character_name: string;
    skill: Skill;
  } | null>(null);
  const [targetSide, setTargetSide] = useState<"enemy" | "ally" | "self" | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const floatId = useRef(0);
  const splashSeenRef = useRef<Set<string>>(new Set());
  const queueRef = useRef<QueuedAction[]>([]);
  // Mirror state into a ref so async callbacks (ws.onclose) read the latest
  // value without being re-created on every render.
  const stateRef = useRef<MatchState | null>(null);
  // Reconnect bookkeeping: ref-based so backoff doesn't churn React renders.
  const wantConnectedRef = useRef(false);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<number | null>(null);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);
  const [nextReconnectAtMs, setNextReconnectAtMs] = useState<number | null>(null);
  const [reconnectGaveUp, setReconnectGaveUp] = useState(false);

  // 1s, 2s, 4s, 8s, 16s — capped so we don't spin forever; 6 attempts cover
  // the server's 30s forfeit grace plus a safety buffer.
  const MAX_RECONNECT_ATTEMPTS = 6;
  const computeBackoffMs = (attempt: number): number =>
    Math.min(16_000, 1_000 * 2 ** Math.min(attempt, 4));

  const toggleMute = () => {
    setMuted((prev) => {
      const next = !prev;
      window.localStorage.setItem(MUTE_KEY, next ? "1" : "0");
      return next;
    });
  };

  const characters = useQuery({ queryKey: ["characters"], queryFn: api.listCharacters });
  const charById = useMemo(() => {
    const map = new Map<string, Character>();
    (characters.data ?? []).forEach((c) => map.set(c.id, c));
    return map;
  }, [characters.data]);

  const floatsByTarget = useMemo(() => {
    const map = new Map<string, FloatingNumber[]>();
    for (const f of floats) {
      const list = map.get(f.target);
      if (list) list.push(f);
      else map.set(f.target, [f]);
    }
    return map;
  }, [floats]);

  useEffect(() => {
    return () => {
      // User left the page — stop reconnect attempts and close cleanly.
      wantConnectedRef.current = false;
      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      wsRef.current?.close();
    };
  }, []);

  // Keep stateRef pointed at the current state for use inside async callbacks.
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    const handle = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(handle);
  }, []);

  useEffect(() => {
    if (!state) return;
    setTurnStartedAt(Date.now());
  }, [state?.turn, state?.current_side]);

  useEffect(() => {
    queueRef.current = queue;
  }, [queue]);

  // Auto-submit ~500ms before deadline
  useEffect(() => {
    if (!state || state.finished || !state.turn_deadline) return;
    const fireAt = Date.parse(state.turn_deadline) - 500;
    const wait = fireAt - Date.now();
    if (wait <= 0) return;
    const handle = window.setTimeout(() => {
      const q = queueRef.current;
      if (q.length === 0) return;
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      ws.send(JSON.stringify({ type: "actions", actions: q }));
    }, wait);
    return () => window.clearTimeout(handle);
  }, [state?.turn_deadline, state?.finished]);

  // Show VS splash on turn 1
  useEffect(() => {
    if (!state || state.turn !== 1 || state.finished) return;
    if (splashSeenRef.current.has(state.match_id)) return;
    splashSeenRef.current.add(state.match_id);
    setSplashFor(state.match_id);
    const handle = window.setTimeout(() => setSplashFor(null), 2000);
    return () => window.clearTimeout(handle);
  }, [state?.match_id, state?.turn, state?.finished]);

  useEffect(() => {
    if (!params.matchId) return;
    (async () => {
      try {
        const response = await fetch(`/api/match/${params.matchId}`);
        if (!response.ok) throw new Error(await response.text());
        setMatchId(params.matchId!);
        setState(await response.json());
        connect(params.matchId!);
      } catch (e) {
        setError(String(e));
      }
    })();
  }, [params.matchId]);

  const startMatch = async () => {
    setError(null);
    try {
      const response = await fetch("/api/match/dev/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          team_a: DEMO_TEAM_A,
          team_b: DEMO_TEAM_B,
          arena_id: "olympus",
          seed: Math.floor(Math.random() * 1000),
        }),
      });
      if (!response.ok) throw new Error(await response.text());
      const data = await response.json();
      setMatchId(data.match_id);
      setState(data.state);
      connect(data.match_id);
    } catch (e) {
      setError(String(e));
    }
  };

  const spawnFloats = (incoming: MatchEvent[]) => {
    const additions: FloatingNumber[] = [];
    for (const e of incoming) {
      if (e.kind !== "damage" && e.kind !== "heal") continue;
      const target = e.details.target;
      const value = e.details.value;
      if (typeof target !== "string" || typeof value !== "number" || value <= 0) continue;
      additions.push({
        id: ++floatId.current,
        target,
        value,
        kind: e.kind,
        tick: typeof e.details.tick === "string" ? e.details.tick : undefined,
      });
    }
    if (additions.length === 0) return;
    setFloats((prev) => [...prev, ...additions]);
    if (additions.some((f) => f.kind === "damage")) playBeep("damage");
    if (additions.some((f) => f.kind === "heal")) playBeep("heal");
    window.setTimeout(() => {
      const ids = new Set(additions.map((f) => f.id));
      setFloats((prev) => prev.filter((f) => !ids.has(f.id)));
    }, 1400);
  };

  const scheduleReconnect = (id: string) => {
    if (!wantConnectedRef.current) return;
    if (reconnectTimerRef.current !== null) return;  // already scheduled
    if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
      setReconnectGaveUp(true);
      return;
    }
    const delay = computeBackoffMs(reconnectAttemptsRef.current);
    reconnectAttemptsRef.current += 1;
    setReconnectAttempt(reconnectAttemptsRef.current);
    setNextReconnectAtMs(Date.now() + delay);
    reconnectTimerRef.current = window.setTimeout(() => {
      reconnectTimerRef.current = null;
      connect(id);
    }, delay);
  };

  const connect = (id: string) => {
    wantConnectedRef.current = true;
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const token = auth.getToken();
    const url = new URL(`${proto}//${window.location.host}/api/match/ws/${id}`);
    if (token) url.searchParams.set("token", token);
    setWsStatus("connecting");
    const ws = new WebSocket(url.toString());
    ws.onopen = () => {
      setWsStatus("open");
      reconnectAttemptsRef.current = 0;
      setReconnectAttempt(0);
      setNextReconnectAtMs(null);
      setReconnectGaveUp(false);
    };
    ws.onclose = () => {
      setWsStatus("closed");
      // Schedule a reconnect unless the user navigated away or the match
      // already ended (server's final state frame would have finished it).
      if (wantConnectedRef.current && !stateRef.current?.finished) {
        scheduleReconnect(id);
      }
    };
    ws.onmessage = (msg) => {
      const frame = JSON.parse(msg.data);
      if (frame.type === "state") {
        setState(frame.state);
        setQueue([]);
        // Initial state frame carries the side this socket controls. Dev
        // hot-seat sends null and we leave the local state as-is.
        if (frame.your_side === "A" || frame.your_side === "B") {
          setYourSide(frame.your_side);
        }
        if (Array.isArray(frame.events)) {
          const newEvents = frame.events as MatchEvent[];
          setEvents((prev) => (frame.auto_resolved ? [...prev, { kind: "turn_auto_resolved", details: {} }, ...newEvents] : [...prev, ...newEvents]));
          spawnFloats(newEvents);
        }
      } else if (frame.type === "presence") {
        if (frame.status === "disconnected" && typeof frame.forfeit_deadline === "string") {
          setOpponentOffline({
            playerId: String(frame.player_id ?? ""),
            forfeitDeadlineMs: Date.parse(frame.forfeit_deadline),
          });
        } else if (frame.status === "reconnected") {
          setOpponentOffline(null);
        }
      } else if (frame.type === "error") {
        // Prefer the localized lookup keyed by the server's stable `code`;
        // fall back to the English `detail` for older frames (or codes
        // that haven't made it into en.ts/pt_BR.ts yet).
        const code = typeof frame.code === "string" ? frame.code : null;
        const detail = typeof frame.detail === "string" ? frame.detail : "Error";
        setError(code ? t(`error.${code}`, detail) : detail);
      }
    };
    ws.onerror = () => {
      setError("WebSocket error");
      setWsStatus("closed");
    };
    wsRef.current = ws;
  };

  const submitTurn = () => {
    wsRef.current?.send(JSON.stringify({ type: "actions", actions: queue }));
  };

  if (!state) {
    // Three sub-cases collapse into "no state": loading a known match id,
    // an error on initial GET, and the dev landing page. Each gets its own
    // affordance instead of all three rendering the same Start button.
    const loadingExisting = Boolean(params.matchId) && error === null;
    const failedExisting = Boolean(params.matchId) && error !== null;

    if (loadingExisting) {
      return <BattleLoadingSkeleton matchId={params.matchId!} />;
    }
    if (failedExisting) {
      return (
        <div className="mx-auto mt-16 max-w-md rounded-xl bg-slate-900 p-6 ring-1 ring-rose-500/40">
          <h2 className="text-xl font-bold text-rose-300">{t("battle.couldntLoad")}</h2>
          <p className="mt-2 break-words text-sm text-slate-400">{error}</p>
          <div className="mt-4 flex gap-3">
            <button
              type="button"
              onClick={() => {
                setError(null);
                window.location.reload();
              }}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold hover:bg-blue-500"
            >
              {t("common.retry")}
            </button>
            <a
              href="/matchmaking"
              className="rounded-md bg-slate-800 px-4 py-2 text-sm ring-1 ring-slate-700 hover:bg-slate-700"
            >
              {t("battle.backToMatchmaking")}
            </a>
          </div>
        </div>
      );
    }
    return (
      <div className="p-8">
        <h2 className="mb-4 text-2xl font-bold">{t("battle.demoTitle")}</h2>
        <p className="mb-4 text-sm text-slate-400">
          {t("battle.demoTagline", undefined, {
            teamA: DEMO_TEAM_A.join("/"),
            teamB: DEMO_TEAM_B.join("/"),
          })}
        </p>
        <button
          type="button"
          onClick={startMatch}
          className="rounded-md bg-emerald-600 px-4 py-2 font-medium hover:bg-emerald-500"
        >
          {t("battle.startMatch")}
        </button>
        {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
      </div>
    );
  }

  // In real matches `yourSide` pins the bottom team to whoever this socket
  // controls — Bob never sees Alice's controls and vice versa, even on
  // her turn. Dev hot-seat (`yourSide === null`) keeps following whoever
  // is currently acting so the same client can play both sides locally.
  const mySide = yourSide ?? state.current_side;
  const activePlayer = mySide === "A" ? state.a : state.b;
  const opponent = mySide === "A" ? state.b : state.a;
  // Only the side whose turn it is may queue actions. In dev hot-seat
  // mySide always equals current_side so this is always true; in real
  // matches it locks the controls during the opponent's turn.
  const isMyTurn = state.current_side === mySide;
  const remainingPool = queue.reduce((pool, action) => subtractPayment(pool, action.paid), activePlayer.essences);
  const charactersAlreadyActing = new Set(queue.map((a) => a.character_id));

  const serverDeadline = state.turn_deadline ? Date.parse(state.turn_deadline) : null;
  const localDeadline = turnStartedAt + TURN_TIMER_SECONDS * 1000;
  const deadlineMs = state.finished ? null : (serverDeadline ?? localDeadline);
  const totalMs = TURN_TIMER_SECONDS * 1000;
  const remainingMs = deadlineMs === null ? 0 : Math.max(0, deadlineMs - now);
  const timerRatio = deadlineMs === null ? 0 : Math.max(0, Math.min(1, remainingMs / totalMs));
  const secondsLeft = Math.ceil(remainingMs / 1000);

  const offlineBanner = state.finished ? null : opponentOffline;
  const offlineSecondsLeft = offlineBanner ? Math.max(0, Math.ceil((offlineBanner.forfeitDeadlineMs - now) / 1000)) : 0;

  // Self-disconnect overlay: shown when we've actually been dropped (status
  // closed, not just the initial "connecting" handshake) and the match isn't
  // yet finished. Goes away as soon as the WebSocket reopens or the server
  // forfeits us.
  const showSelfDisconnect = !state.finished && wsStatus === "closed";
  const reconnectIn = nextReconnectAtMs ? Math.max(0, Math.ceil((nextReconnectAtMs - now) / 1000)) : 0;

  const onSkillClick = (character: CharacterState, skill: Skill) => {
    if (!isMyTurn) return;  // server would reject anyway; bail before flicker
    const paid = computePayment(skill.cost, remainingPool);
    if (paid === null) return;

    setSelectedSkill({ character_id: character.id, character_name: character.name, skill });

    if (skill.target === "self") {
      setTargetSide("self");
    } else if (skill.target === "single_enemy" || skill.target === "all_enemies") {
      setTargetSide("enemy");
    } else {
      setTargetSide("ally");
    }
  };

  const enqueue = (action: QueuedAction) => {
    setQueue((prev) => [...prev, action]);
    setSelectedSkill(null);
    setTargetSide(null);
  };

  const onTargetClick = (targetId: string) => {
    if (!selectedSkill) return;
    const skill = selectedSkill.skill;
    // For self: guard against clicking the wrong character (belt-and-suspenders)
    if (targetSide === "self" && targetId !== selectedSkill.character_id) return;
    let target_ids: string[];
    if (skill.target === "all_enemies") {
      target_ids = opponent.characters.map((c) => c.id);
    } else if (skill.target === "all_allies") {
      target_ids = activePlayer.characters.map((c) => c.id);
    } else {
      target_ids = [targetId];
    }
    enqueue({
      character_id: selectedSkill.character_id,
      skill_id: skill.id,
      target_ids,
      paid: computePayment(skill.cost, remainingPool) ?? {},
    });
  };

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{
        backgroundImage: "url('/arena-bg.svg')",
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundRepeat: "no-repeat",
      }}
    >
      {/* Dark overlay so UI stays readable */}
      <div className="absolute inset-0 bg-slate-950/70 pointer-events-none" />
      <div className="relative flex flex-col min-h-screen">
        <VsSplash visible={splashFor === state.match_id} teamA={state.a.characters} teamB={state.b.characters} />

        {showSelfDisconnect && (
          <ReconnectOverlay
            gaveUp={reconnectGaveUp}
            attempt={reconnectAttempt}
            maxAttempts={MAX_RECONNECT_ATTEMPTS}
            secondsUntilNext={reconnectIn}
            onRetry={() => {
              if (matchId) {
                reconnectAttemptsRef.current = 0;
                setReconnectAttempt(0);
                setReconnectGaveUp(false);
                connect(matchId);
              }
            }}
          />
        )}

        {offlineBanner && (
          <div className="mx-4 mt-4 flex items-center rounded-lg bg-amber-500/10 px-4 py-2 text-xs text-amber-200 ring-1 ring-amber-500/40">
            <span>
              {t("battle.opponentDisconnected", undefined, {
                seconds: offlineSecondsLeft,
              })
                .split(/(\d+s)/)
                .map((part, i) =>
                  /^\d+s$/.test(part) ? (
                    <span key={i} className="font-mono font-bold text-amber-100">
                      {part}
                    </span>
                  ) : (
                    <span key={i}>{part}</span>
                  ),
                )}
            </span>
          </div>
        )}

        {/* HEADER */}
        <header className="border-b border-slate-800 bg-slate-900/80 px-6 py-3">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-3 text-sm text-slate-400">
              <ConnectionDot status={wsStatus} />
              <span className="font-mono text-slate-500">match {matchId?.slice(0, 8)}</span>
              <span className="text-slate-700">·</span>
              <span>arena {state.arena_id}</span>
            </div>
            <div className="text-center">
              <div className="text-xs uppercase tracking-wider text-slate-500">Turn</div>
              <div className="text-2xl font-bold tabular-nums">{state.turn}</div>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-right text-sm">
                <div className="text-xs uppercase tracking-wider text-slate-500">
                  {isMyTurn
                    ? t("battle.yourTurn", undefined, { seconds: secondsLeft })
                    : t("battle.opponentTurn", undefined, { seconds: secondsLeft })}
                </div>
                <div
                  className={
                    isMyTurn
                      ? "font-bold text-emerald-400"
                      : "font-bold text-rose-400"
                  }
                >
                  Side {state.current_side}
                </div>
              </div>
              <button
                type="button"
                onClick={toggleMute}
                aria-label={muted ? "Unmute" : "Mute"}
                className="rounded-md bg-slate-800 px-2 py-1 text-lg leading-none text-slate-300 ring-1 ring-slate-700 hover:bg-slate-700"
              >
                {muted ? "\u{1F507}" : "\u{1F50A}"}
              </button>
            </div>
          </div>
          {!state.finished && (
            <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
              <div
                className={[
                  "h-full transition-[width] duration-200 ease-linear",
                  timerRatio > 0.5 ? "bg-emerald-500" : timerRatio > 0.2 ? "bg-amber-400" : "bg-red-500",
                ].join(" ")}
                style={{ width: `${timerRatio * 100}%` }}
              />
            </div>
          )}
        </header>

        {/* BATTLE AREA - Side by side */}
        <div className="flex-1 flex gap-4 p-4 overflow-hidden">
          {/* LEFT: YOUR TEAM */}
          <BattleSide
            title={`Your team · Side ${activePlayer.side}`}
            side="player"
            characters={activePlayer.characters}
            player={activePlayer}
            charById={charById}
            floatsByTarget={floatsByTarget}
            isActive={state.current_side === activePlayer.side}
            queued={charactersAlreadyActing}
            selectedSkillCharId={selectedSkill?.character_id}
            targetSide={targetSide}
            onSkillClick={onSkillClick}
            onTargetClick={targetSide === "ally" || targetSide === "self" ? onTargetClick : undefined}
            remainingPool={remainingPool}
          />

          {/* CENTER: CONTROLS */}
          <div className="w-80 flex flex-col gap-4">
            {/* Essence Info */}
            <div className="bg-slate-900/80 rounded-lg ring-1 ring-slate-800 p-4 space-y-3">
              <div>
                <div className="text-xs uppercase tracking-wider text-slate-500 mb-2">Your essences</div>
                <EssenceBar pool={activePlayer.essences} large />
              </div>
              <div className="h-px bg-slate-700" />
              <div>
                <div className="text-xs uppercase tracking-wider text-slate-500 mb-2">Available</div>
                <EssenceBar pool={remainingPool} large />
              </div>
            </div>

            {/* Skill Detail (inline, read-only) */}
            <AnimatePresence>
              {selectedSkill && (
                <motion.div
                  key={selectedSkill.skill.id}
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.15 }}
                  className="bg-slate-900/90 rounded-lg ring-1 ring-amber-500/40 p-4 space-y-3"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="text-base font-bold text-amber-200">{selectedSkill.skill.name}</div>
                      <div className="text-[10px] text-slate-400">{selectedSkill.character_name}</div>
                    </div>
                    <button
                      type="button"
                      onClick={() => { setSelectedSkill(null); setTargetSide(null); }}
                      className="text-slate-500 hover:text-slate-300 text-lg leading-none"
                    >×</button>
                  </div>
                  {/* Naruto Arena-style description */}
                  <p className="text-[13px] leading-relaxed text-slate-100 border-l-2 border-amber-500/60 pl-3">
                    {selectedSkill.skill.description?.trim()
                      ? selectedSkill.skill.description
                      : buildSkillDescription(selectedSkill.skill)}
                  </p>

                  {/* Meta row: cost + cooldown */}
                  <div className="flex items-center justify-between gap-2 pt-1 border-t border-slate-700/60">
                    <div className="flex gap-1 flex-wrap">
                      {Object.keys(selectedSkill.skill.cost).length === 0 ? (
                        <span className="text-[10px] italic text-slate-500">No cost</span>
                      ) : (
                        Object.entries(selectedSkill.skill.cost).map(([e, n]) => (
                          <span key={e} className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ring-1 ${ESSENCE_STYLE[e as Essence].chip}`}>
                            <span className={`inline-block h-1.5 w-1.5 rounded-full mr-1 ${ESSENCE_STYLE[e as Essence].dot}`} />
                            {n}× {ESSENCE_STYLE[e as Essence].label}
                          </span>
                        ))
                      )}
                    </div>
                    <div className="flex gap-3 text-[10px] text-slate-500 shrink-0">
                      {selectedSkill.skill.cooldown > 0 && (
                        <span>CD <span className="text-slate-300 font-bold">{selectedSkill.skill.cooldown}</span></span>
                      )}
                      {selectedSkill.skill.duration > 0 && (
                        <span>DUR <span className="text-slate-300 font-bold">{selectedSkill.skill.duration}</span></span>
                      )}
                    </div>
                  </div>
                  {targetSide && (
                    <p className="text-[10px] text-amber-400/70 italic">
                      {targetSide === "enemy"
                        ? selectedSkill.skill.target === "all_enemies"
                          ? "→ Click any opponent to hit all enemies"
                          : "→ Click an opponent to cast"
                        : targetSide === "self"
                          ? "→ Click the same character to cast"
                          : selectedSkill.skill.target === "all_allies"
                            ? "→ Click any ally to buff all allies"
                            : "→ Click an ally to cast"}
                    </p>
                  )}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Turn timer */}
            {!state.finished && (() => {
              const TURN_SECS = 60;
              const elapsed = (now - turnStartedAt) / 1000;
              const secondsLeft = Math.max(0, Math.ceil(TURN_SECS - elapsed));
              const progress = Math.max(0, 1 - elapsed / TURN_SECS);
              const urgent = secondsLeft <= 10;
              return (
                <div className="bg-slate-900/80 rounded-lg ring-1 ring-slate-800 px-3 py-2">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Turn timer</span>
                    <span className={`text-xs font-mono font-bold ${urgent ? "text-rose-400 animate-pulse" : "text-slate-300"}`}>
                      {secondsLeft}s
                    </span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-slate-700 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-300 ${urgent ? "bg-rose-500" : "bg-blue-500"}`}
                      style={{ width: `${progress * 100}%` }}
                    />
                  </div>
                </div>
              );
            })()}

            {/* Queue */}
            {!state.finished && (
              <div className="bg-slate-900/80 rounded-lg ring-1 ring-slate-800 p-4 flex-1 flex flex-col">
                <div className="text-xs uppercase tracking-wider text-slate-500 mb-3 font-semibold">
                  {queue.length === 0 ? "No actions" : `${queue.length}/3 queued`}
                </div>
                <div className="flex-1 overflow-y-auto space-y-2 mb-3">
                  {queue.map((action, i) => {
                    const def = charById.get(action.character_id);
                    const skill = def?.skills.find((s) => s.id === action.skill_id);
                    return (
                      <div key={i} className="flex items-center justify-between gap-2 rounded-md bg-slate-800 px-2 py-1.5 text-xs ring-1 ring-slate-700">
                        <div className="min-w-0 flex-1">
                          <div className="font-semibold truncate text-slate-100">{def?.name}</div>
                          <div className="text-slate-400 text-[10px] truncate">{skill?.name}</div>
                        </div>
                        <button
                          type="button"
                          onClick={() => setQueue((prev) => prev.filter((_, idx) => idx !== i))}
                          className="text-rose-400 hover:text-rose-300 flex-shrink-0"
                        >
                          ×
                        </button>
                      </div>
                    );
                  })}
                </div>
                <div className="flex flex-col gap-3">
                  <button
                    type="button"
                    onClick={submitTurn}
                    disabled={!isMyTurn}
                    className="rounded-md bg-blue-600 px-3 py-2 text-xs font-medium hover:bg-blue-500 w-full disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-500"
                  >
                    {isMyTurn ? t("battle.confirmTurn") : t("battle.opponentTurnLabel")}
                  </button>
                  <button
                    type="button"
                    onClick={() => setQueue([])}
                    disabled={!isMyTurn}
                    className="rounded-md bg-slate-700 px-3 py-2 text-xs font-medium hover:bg-slate-600 w-full disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {t("battle.clear")}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* RIGHT: OPPONENT */}
          <BattleSide
            title={`Opponent · Side ${opponent.side}`}
            side="opponent"
            characters={opponent.characters}
            player={opponent}
            charById={charById}
            floatsByTarget={floatsByTarget}
            isActive={false}
            queued={new Set()}
            selectedSkillCharId={selectedSkill?.character_id}
            targetSide={targetSide}
            onSkillClick={() => { }}
            onTargetClick={targetSide === "enemy" ? onTargetClick : undefined}
          />
        </div>

        {error && <p className="text-sm text-red-400 fixed bottom-4 left-4">{error}</p>}
      </div>
    </div>
  );
}

// ============================================================================
// COMPONENTS
// ============================================================================

function BattleSide({
  title,
  side = "player",
  characters,
  charById,
  floatsByTarget,
  queued,
  selectedSkillCharId,
  targetSide,
  onSkillClick,
  onTargetClick,
  remainingPool,
  isActive,
}: {
  title: string;
  side?: "player" | "opponent";
  characters: CharacterState[];
  player?: PlayerState;
  charById: Map<string, Character>;
  floatsByTarget: Map<string, FloatingNumber[]>;
  queued: Set<string>;
  selectedSkillCharId?: string;
  targetSide?: "enemy" | "ally" | "self" | null;
  onSkillClick: (character: CharacterState, skill: Skill) => void;
  onTargetClick?: (targetId: string) => void;
  remainingPool?: Partial<Record<Essence, number>>;
  isActive?: boolean;
}) {
  const tone = title.includes("Opponent") ? "rose" : "emerald";
  const bgGradient = tone === "opponent" ? "from-slate-900/60 to-slate-950/60" : "from-slate-900/60 to-slate-950/60";
  const isOpponentSide = side === "opponent";

  return (
    <section className={`flex-1 flex flex-col bg-gradient-to-br ${bgGradient} rounded-lg ring-1 ring-slate-800 p-6 overflow-hidden`}>
      <div className="flex items-center gap-2 mb-4">
        <span className={`inline-block h-2 w-2 rounded-full ${tone === "opponent" ? "bg-rose-400" : "bg-emerald-400"}`} />
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">{title}</h2>
      </div>

      <div className="flex-1 flex flex-col justify-center gap-4">
        {characters.map((c) => {
          const def = charById.get(c.id);
          const isQueued = queued.has(c.id);
          const stunned = c.statuses.some((s) => s.name === "stun");
          const dead = c.hp <= 0;

          const isDimmed = !!targetSide && !dead && (
            isOpponentSide
              ? targetSide === "ally" || targetSide === "self"
              : targetSide === "enemy" || (targetSide === "self" && c.id !== selectedSkillCharId)
          );
          const isClickable = !!onTargetClick && !dead &&
            (targetSide !== "self" || c.id === selectedSkillCharId);
          return (
            <div key={c.id} className="flex-1 flex flex-col gap-2">
              <CharacterPortrait
                character={c}
                floats={floatsByTarget.get(c.id) ?? []}
                queued={isQueued}
                isOpponent={tone === "rose"}
                clickable={isClickable}
                dimmed={isDimmed}
                charById={charById}
                onClick={isClickable ? () => onTargetClick(c.id) : undefined}
              />

              {remainingPool && def && !dead && isActive && !isQueued && (
                <SkillGrid character={c} def={def} remainingPool={remainingPool} stunned={stunned} onSkillClick={onSkillClick} />
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

const STATUS_DESCRIPTIONS: Record<string, string> = {
  poison:           "Deals damage each turn based on value.",
  bleed:            "Deals damage each turn. Removed when healed.",
  stun:             "Cannot act this turn.",
  silence:          "Cannot use non-physical skills.",
  disarm:           "Cannot use physical skills.",
  stealth:          "Cannot be targeted by single-target skills.",
  reflective:       "Reflects a portion of damage back to the attacker.",
  invulnerable:     "Immune to all damage and harmful effects.",
  damage_reduction: "Incoming damage is reduced by the stack value.",
  damage_buff:      "Outgoing damage is increased by the stack value.",
  regen:            "Recovers HP at the start of each turn.",
  vulnerable:       "Cannot resist new negative status effects.",
  marked:           "Takes bonus damage from all sources.",
  drained:          "Loses essence each turn.",
  shield:           "Absorbs incoming damage before HP is reduced. Lasts until depleted.",
};

function StatusBadge({
  status,
  charById,
}: {
  status: CharacterState["statuses"][number];
  charById: Map<string, Character>;
}) {
  const [hovered, setHovered] = useState(false);

  const sourceChar = status.source ? charById.get(status.source) : null;
  const sourceSkill = sourceChar?.skills.find((sk) =>
    sk.effects.some(
      (e) =>
        (e.kind === "status" && e.status === status.name) ||
        (e.kind === status.name as string) ||
        (status.name === "shield" && e.kind === "destructible_shield")
    )
  );
  const iconUrl = sourceSkill && sourceChar
    ? `/skills/${sourceChar.id}_${sourceSkill.id}.png`
    : null;

  const isHarmful = ["poison", "bleed", "stun", "silence", "disarm", "marked", "drained", "vulnerable"].includes(status.name);
  const badgeColor = status.name === "shield"
    ? "bg-cyan-950/80 text-cyan-300 ring-cyan-800"
    : isHarmful
    ? "bg-rose-950/80 text-rose-300 ring-rose-800"
    : "bg-emerald-950/80 text-emerald-300 ring-emerald-800";

  return (
    <div
      className="relative"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {hovered && (
        <div className="pointer-events-none absolute z-50 bottom-[calc(100%+5px)] left-0 w-44 rounded-lg bg-slate-950 ring-1 ring-slate-700 shadow-2xl p-2 flex flex-col gap-1.5">
          <div className="absolute top-full left-3 border-4 border-transparent border-t-slate-950" />
          {iconUrl && (
            <div className="h-8 w-full rounded overflow-hidden bg-slate-800">
              <img src={iconUrl} alt="" className="h-full w-full object-cover" onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }} />
            </div>
          )}
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-100">
            {status.name.replace(/_/g, " ")}
            {status.value > 0 && <span className="ml-1 font-mono text-slate-400">{status.value}</span>}
          </div>
          <p className="text-[10px] text-slate-400 leading-relaxed">
            {STATUS_DESCRIPTIONS[status.name] ?? "Active status effect."}
          </p>
          <div className="text-[10px] text-slate-500">
            Duration: <span className="text-slate-300 font-mono">{status.duration === -1 ? "∞" : status.duration}</span>{status.duration !== -1 && (status.duration !== 1 ? " turns" : " turn")}
          </div>
        </div>
      )}
      <div className={`rounded overflow-hidden ring-1 cursor-default ${badgeColor} ${iconUrl ? "h-8 w-14" : "px-1.5 py-0.5 text-[10px] uppercase tracking-wider"}`}>
        {iconUrl ? (
          <img src={iconUrl} alt={status.name} className="h-full w-full object-cover" />
        ) : (
          status.name.replace(/_/g, " ")
        )}
      </div>
    </div>
  );
}

function CharacterPortrait({
  character,
  floats = [],
  queued = false,
  isOpponent = false,
  clickable = false,
  dimmed = false,
  charById = new Map(),
  onClick,
}: {
  character: CharacterState;
  floats?: FloatingNumber[];
  queued?: boolean;
  isOpponent?: boolean;
  clickable?: boolean;
  dimmed?: boolean;
  charById?: Map<string, Character>;
  onClick?: () => void;
}) {
  const dead = character.hp <= 0;
  const ratio = character.hp_max > 0 ? character.hp / character.hp_max : 0;
  const hpColor = ratio > 0.6 ? "bg-emerald-500" : ratio > 0.3 ? "bg-amber-400" : "bg-red-500";
  const [artBroken, setArtBroken] = useState(false);
  const portraitUrl = `/portraits/${character.id}.jpg`;
  const shakeControls = useAnimationControls();
  const lastShakeIdRef = useRef<number | null>(null);

  useEffect(() => {
    const damages = floats.filter((f) => f.kind === "damage");
    if (damages.length === 0) return;
    const latestId = damages[damages.length - 1].id;
    if (lastShakeIdRef.current === latestId) return;
    lastShakeIdRef.current = latestId;
    shakeControls.start({
      x: [0, -6, 6, -4, 4, 0],
      transition: { duration: 0.4, ease: "easeOut" },
    });
  }, [floats, shakeControls]);

  return (
    <motion.div
      animate={shakeControls}
      onClick={clickable && !dead ? onClick : undefined}
      className={[
        "relative rounded-lg p-3 ring-1 transition",
        dead ? "bg-slate-950/60 ring-slate-900 opacity-50" : "bg-slate-800/90 ring-slate-700",
        queued ? "ring-emerald-500/70 ring-2" : "",
        clickable && !dead ? "cursor-pointer ring-2 ring-amber-400 hover:ring-amber-300 hover:brightness-110" : "",
      ].join(" ")}
    >
      <FloatingNumbers items={floats} />
      {dimmed && <div className="absolute inset-0 rounded-lg bg-slate-950/65 z-10 pointer-events-none" />}
      <div className="flex items-center gap-3">
        <div
          className={[
            "flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-md text-xl font-bold",
            isOpponent ? "bg-rose-900/60 text-rose-200" : "bg-emerald-900/60 text-emerald-200",
            dead ? "grayscale" : "",
          ].join(" ")}
        >
          {artBroken ? (
            character.name.charAt(0).toUpperCase()
          ) : (
            <img src={portraitUrl} alt="" draggable={false} onError={() => setArtBroken(true)} className="h-full w-full object-cover" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-1">
            <span className="truncate text-sm font-semibold">{character.name}</span>
            <span className="font-mono text-xs tabular-nums text-slate-300">
              {character.hp}/{character.hp_max}
            </span>
          </div>
          <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-900">
            <div className={`h-full transition-all ${hpColor}`} style={{ width: `${Math.max(0, Math.min(100, ratio * 100))}%` }} />
          </div>
        </div>
      </div>

      {(character.statuses.length > 0 || character.shield > 0) && (
        <div className="mt-2 flex flex-wrap gap-1">
          {character.shield > 0 && (
            <StatusBadge
              status={{ name: "shield", duration: -1, value: character.shield, source: character.shield_source }}
              charById={charById}
            />
          )}
          {character.statuses.map((s, i) => (
            <StatusBadge key={i} status={s} charById={charById} />
          ))}
        </div>
      )}

      {dead && <div className="absolute inset-0 grid place-items-center bg-slate-950/40 text-xs font-bold uppercase tracking-widest text-red-400">KO</div>}
    </motion.div>
  );
}

function SkillTooltip({ skill, iconUrl, cd }: { skill: Skill; iconUrl: string; cd: number }) {
  return (
    <div className="pointer-events-none absolute z-50 bottom-[calc(100%+6px)] left-1/2 -translate-x-1/2 w-52 rounded-lg bg-slate-950 ring-1 ring-slate-700 shadow-2xl p-2 flex flex-col gap-2">
      <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-950" />
      <div className="flex items-center gap-2">
        <div className="h-10 w-16 shrink-0 rounded overflow-hidden bg-slate-800">
          <img src={iconUrl} alt="" className="h-full w-full object-cover" onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }} />
        </div>
        <div className="min-w-0">
          <div className="text-xs font-bold text-slate-100 leading-tight">{skill.name}</div>
          <div className="mt-0.5 flex items-center gap-1 flex-wrap">
            <CostPips cost={skill.cost} size="small" />
          </div>
        </div>
      </div>
      {skill.description && (
        <p className="text-[10px] text-slate-400 leading-relaxed border-t border-slate-800 pt-1.5">
          {skill.description}
        </p>
      )}
      <div className="flex items-center gap-2 text-[10px] text-slate-500 border-t border-slate-800 pt-1">
        <span>CD <span className="text-slate-300 font-mono">{skill.cooldown}</span></span>
        {cd > 0 && <span className="text-rose-400 font-semibold">on cooldown: {cd}t</span>}
        <span className="ml-auto capitalize">{skill.kind}</span>
      </div>
    </div>
  );
}

function SkillGrid({
  character,
  def,
  remainingPool,
  stunned,
  onSkillClick,
}: {
  character: CharacterState;
  def: Character;
  remainingPool: Partial<Record<Essence, number>>;
  stunned: boolean;
  onSkillClick: (character: CharacterState, skill: Skill) => void;
}) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const DODGE_SKILL: Skill = {
    id: "dodge",
    name: "Dodge",
    kind: "instant",
    cost: { generic: 1 },
    cooldown: 4,
    duration: 0,
    target: "self",
    effects: [{ kind: "invulnerable", value: 0, duration: 1, damage_class: null, status: null, piercing: false, true: false }],
    description: "Spend 1 generic essence to become invulnerable for 1 turn. (4-turn cooldown)",
  };
  const allSkills = [...def.skills, DODGE_SKILL];

  return (
    <div className="grid grid-cols-4 gap-1">
      {allSkills.map((skill) => {
        const cd = character.cooldowns[skill.id] ?? 0;
        const affordable = computePayment(skill.cost, remainingPool) !== null;
        const disabled = stunned || cd > 0 || !affordable;

        const iconUrl = skill.id === "dodge"
          ? `/skills/dodge.png`
          : `/skills/${character.id}_${skill.id}.png`;

        return (
          <div
            key={skill.id}
            className="relative"
            onMouseEnter={() => setHoveredId(skill.id)}
            onMouseLeave={() => setHoveredId(null)}
          >
            {hoveredId === skill.id && (
              <SkillTooltip skill={skill} iconUrl={iconUrl} cd={cd} />
            )}
            <button
              type="button"
              onClick={() => onSkillClick(character, skill)}
              disabled={disabled}
              className={[
                "relative rounded overflow-hidden transition w-full aspect-[418/235]",
                disabled
                  ? "opacity-40 cursor-not-allowed grayscale"
                  : "ring-1 ring-slate-600 hover:ring-amber-400 hover:scale-105 cursor-pointer",
              ].join(" ")}
            >
              <img
                src={iconUrl}
                alt={skill.name}
                className="absolute inset-0 w-full h-full object-cover"
                onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
              />
              <div className="absolute top-0.5 left-0.5 flex gap-px">
                <CostPips cost={skill.cost} size="small" />
              </div>
              {cd > 0 && (
                <div className="absolute top-0.5 right-0.5 bg-rose-600 rounded-full w-5 h-5 flex items-center justify-center text-[9px] font-bold text-white shadow">
                  {cd}
                </div>
              )}
            </button>
          </div>
        );
      })}
    </div>
  );
}

function EssenceBar({ pool, large = false }: { pool: Partial<Record<Essence, number>>; large?: boolean }) {
  const items = ESSENCE_ORDER.filter((k) => (pool[k] ?? 0) > 0);
  if (items.length === 0) {
    return <span className={`${large ? "text-base" : "text-xs"} italic text-slate-600`}>empty</span>;
  }
  return (
    <div className={`flex items-center gap-2 flex-wrap ${large ? "text-base" : "text-xs"}`}>
      {items.map((k) => {
        const style = ESSENCE_STYLE[k];
        const count = pool[k]!;
        return (
          <span key={k} className={`inline-flex items-center gap-1 rounded-full px-2 py-1 ring-1 ${style.chip}`} title={k}>
            <span className={`inline-block h-2 w-2 rounded-full ${style.dot}`} />
            <span className="font-mono font-semibold">{count}</span>
            <span className="opacity-70 text-xs">{style.label}</span>
          </span>
        );
      })}
    </div>
  );
}

function CostPips({ cost, size = "normal" }: { cost: Partial<Record<Essence, number>>; size?: "small" | "normal" }) {
  const pips: { color: string; key: string }[] = [];
  for (const k of ESSENCE_ORDER) {
    const n = cost[k] ?? 0;
    for (let i = 0; i < n; i++) pips.push({ color: ESSENCE_STYLE[k].dot, key: `${k}${i}` });
  }
  const generic = cost.generic ?? 0;
  for (let i = 0; i < generic; i++) {
    pips.push({ color: ESSENCE_STYLE.generic.dot, key: `g${i}` });
  }
  if (pips.length === 0) {
    return <span className="text-[9px] italic text-slate-500">free</span>;
  }
  const pipSize = size === "small" ? "h-1.5 w-1.5" : "h-2 w-2";
  return (
    <span className="flex items-center gap-0.5">
      {pips.map((p) => (
        <span key={p.key} className={`inline-block rounded-full ${p.color} ${pipSize}`} />
      ))}
    </span>
  );
}

function FloatingNumbers({ items }: { items: FloatingNumber[] }) {
  return (
    <div className="pointer-events-none absolute inset-0">
      {items.map((item) => (
        <motion.div
          key={item.id}
          initial={{ opacity: 1, y: 0 }}
          animate={{ opacity: 0, y: -60 }}
          transition={{ duration: 1.4, ease: "easeOut" }}
          className={`absolute text-sm font-bold ${item.kind === "damage" ? "text-rose-400" : "text-emerald-400"}`}
          style={{ left: "50%", top: "50%" }}
        >
          {item.value}
        </motion.div>
      ))}
    </div>
  );
}

function BattleLoadingSkeleton({ matchId }: { matchId: string }) {
  const t = useT();
  return (
    <div className="mx-auto flex min-h-screen max-w-5xl flex-col gap-4 px-4 py-6 animate-pulse">
      <div className="rounded-xl bg-slate-900/80 px-5 py-3 ring-1 ring-slate-800">
        <div className="h-4 w-40 rounded bg-slate-800" />
        <div className="mt-2 h-3 w-24 rounded bg-slate-800/60" />
      </div>
      <div className="rounded-xl bg-slate-900/40 p-4 ring-1 ring-slate-800">
        <div className="grid grid-cols-3 gap-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="rounded-lg bg-slate-800/60 p-3">
              <div className="h-12 w-full rounded bg-slate-800" />
              <div className="mt-2 h-2 w-3/4 rounded bg-slate-800" />
              <div className="mt-1 h-2 w-1/2 rounded bg-slate-800/70" />
            </div>
          ))}
        </div>
      </div>
      <div className="rounded-xl bg-slate-900/80 px-5 py-3 ring-1 ring-slate-800">
        <div className="h-4 w-32 rounded bg-slate-800" />
      </div>
      <div className="rounded-xl bg-slate-900/40 p-4 ring-1 ring-slate-800">
        <div className="grid grid-cols-3 gap-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="rounded-lg bg-slate-800/60 p-3">
              <div className="h-12 w-full rounded bg-slate-800" />
              <div className="mt-2 h-2 w-3/4 rounded bg-slate-800" />
            </div>
          ))}
        </div>
      </div>
      <p className="text-center text-xs text-slate-500">
        {t("battle.loadingMatch", undefined, { id: matchId.slice(0, 8) })}
      </p>
    </div>
  );
}

function ReconnectOverlay({
  gaveUp,
  attempt,
  maxAttempts,
  secondsUntilNext,
  onRetry,
}: {
  gaveUp: boolean;
  attempt: number;
  maxAttempts: number;
  secondsUntilNext: number;
  onRetry: () => void;
}) {
  const t = useT();
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/85 backdrop-blur-sm">
      <div className="max-w-md rounded-xl bg-slate-900 px-6 py-5 text-center ring-1 ring-slate-800 shadow-xl">
        {gaveUp ? (
          <>
            <div className="mb-2 text-2xl">⚠</div>
            <div className="text-lg font-bold text-rose-300">{t("reconnect.connectionLost")}</div>
            <p className="mt-2 text-sm text-slate-400">{t("reconnect.connectionLostBody")}</p>
            <button
              type="button"
              onClick={onRetry}
              className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold hover:bg-blue-500"
            >
              {t("common.tryAgain")}
            </button>
          </>
        ) : (
          <>
            <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-slate-700 border-t-amber-400" />
            <div className="text-lg font-bold text-amber-200">{t("reconnect.reconnecting")}</div>
            <p className="mt-2 text-xs text-slate-400">
              {t("reconnect.attempt", undefined, {
                current: Math.max(1, attempt),
                max: maxAttempts,
              })}
              {secondsUntilNext > 0 && (
                <>
                  {" · "}
                  {t("reconnect.nextIn", undefined, { seconds: secondsUntilNext })
                    .split(/(\d+s)/)
                    .map((part, i) =>
                      /^\d+s$/.test(part) ? (
                        <span key={i} className="font-mono text-slate-200">
                          {part}
                        </span>
                      ) : (
                        <span key={i}>{part}</span>
                      ),
                    )}
                </>
              )}
            </p>
            <button
              type="button"
              onClick={onRetry}
              className="mt-4 rounded-md bg-slate-800 px-3 py-1.5 text-xs text-slate-300 ring-1 ring-slate-700 hover:bg-slate-700"
            >
              {t("reconnect.retryNow")}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function ConnectionDot({ status }: { status: "connecting" | "open" | "closed" }) {
  const profile =
    status === "open"
      ? { color: "bg-emerald-400", label: "live", pulse: true }
      : status === "connecting"
        ? { color: "bg-amber-400", label: "connecting", pulse: true }
        : { color: "bg-red-500", label: "offline", pulse: false };
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-950/60 px-2 py-0.5 text-[10px] uppercase tracking-wider text-slate-400 ring-1 ring-slate-800">
      <span className="relative flex h-2 w-2">
        {profile.pulse && <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-60 ${profile.color}`} />}
        <span className={`relative inline-flex h-2 w-2 rounded-full ${profile.color}`} />
      </span>
      {profile.label}
    </span>
  );
}

function VsSplash({ visible, teamA, teamB }: { visible: boolean; teamA: CharacterState[]; teamB: CharacterState[] }) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="splash"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.25 }}
          className="pointer-events-none fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm"
        >
          <motion.div initial={{ x: -180, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ delay: 0.05, type: "spring", stiffness: 200, damping: 18 }} className="text-right">
            <div className="text-[10px] font-semibold uppercase tracking-[0.4em] text-emerald-400">Side A</div>
            <div className="text-3xl font-bold text-emerald-100">{teamA.map((c) => c.name).join(" · ")}</div>
          </motion.div>

          <motion.div
            initial={{ scale: 0.4, opacity: 0, rotate: -10 }}
            animate={{ scale: 1, opacity: 1, rotate: 0 }}
            transition={{ delay: 0.15, type: "spring", stiffness: 260, damping: 14 }}
            className="mx-6 select-none text-7xl font-black italic tracking-tight text-amber-400 drop-shadow-[0_0_18px_rgba(251,191,36,0.45)]"
          >
            VS
          </motion.div>

          <motion.div initial={{ x: 180, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ delay: 0.05, type: "spring", stiffness: 200, damping: 18 }} className="text-left">
            <div className="text-[10px] font-semibold uppercase tracking-[0.4em] text-rose-400">Side B</div>
            <div className="text-3xl font-bold text-rose-100">{teamB.map((c) => c.name).join(" · ")}</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// ============================================================================
// HELPERS
// ============================================================================

function targetLabel(target: string): string {
  switch (target) {
    case "single_enemy": return "one enemy";
    case "all_enemies": return "all enemies";
    case "single_ally": return "one ally";
    case "all_allies": return "all allies";
    case "self": return "this character";
    default: return "the target";
  }
}

function buildSkillDescription(skill: Skill): string {
  const parts: string[] = [];
  for (const ef of skill.effects) {
    const tgt = targetLabel(skill.target);
    switch (ef.kind) {
      case "damage": {
        const cls = ef.damage_class ? `${ef.damage_class} ` : "";
        let s = `Deals ${ef.value} ${cls}damage to ${tgt}.`;
        if (ef.piercing) s += " Ignores damage reduction.";
        parts.push(s);
        break;
      }
      case "heal":
        parts.push(`Restores ${ef.value} HP to ${tgt}.`);
        break;
      case "status":
        parts.push(
          `Inflicts ${ef.status ?? "a status effect"} on ${tgt}` +
          (ef.duration > 0 ? ` for ${ef.duration} turn${ef.duration !== 1 ? "s" : ""}` : "") +
          "."
        );
        break;
      case "destructible_shield":
        parts.push(`Grants ${tgt} ${ef.value} points of destructible defense.`);
        break;
      case "invulnerable":
        parts.push(
          `Makes ${tgt} invulnerable for ${ef.duration} turn${ef.duration !== 1 ? "s" : ""}.`
        );
        break;
      case "damage_reduction":
        parts.push(
          `Reduces damage taken by ${tgt} by ${ef.value}` +
          (ef.duration > 0 ? ` for ${ef.duration} turn${ef.duration !== 1 ? "s" : ""}` : "") +
          "."
        );
        break;
      case "damage_buff":
        parts.push(
          `Increases damage dealt by ${tgt} by ${ef.value}` +
          (ef.duration > 0 ? ` for ${ef.duration} turn${ef.duration !== 1 ? "s" : ""}` : "") +
          "."
        );
        break;
      case "essence_drain":
        parts.push(`Drains ${ef.value} essence from ${tgt}.`);
        break;
      case "remove_afflictions":
        parts.push(`Removes all afflictions from ${tgt}.`);
        break;
    }
  }
  if (skill.cooldown > 0)
    parts.push(`Enters a ${skill.cooldown}-turn cooldown after use.`);
  return parts.join(" ") || "No description available.";
}

function describeSkill(skill: Skill): string {
  return buildSkillDescription(skill);
}
