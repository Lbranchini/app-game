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
import type { Character, Essence, Skill } from "@/types/api";

// --------------------------------------------------------------------------- //
// Types mirroring the MatchState payload                                      //
// --------------------------------------------------------------------------- //

interface CharacterState {
  id: string;
  name: string;
  hp: number;
  hp_max: number;
  shield: number;
  cooldowns: Record<string, number>;
  statuses: { name: string; duration: number; value: number }[];
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
}

interface MatchEvent {
  kind: string;
  details: Record<string, unknown>;
}

const DEMO_TEAM_A = ["achilles", "athena", "anubis"];
const DEMO_TEAM_B = ["thor", "isis", "loki"];

const ESSENCE_STYLE: Record<Essence, { dot: string; chip: string; label: string }> = {
  vigor:   { dot: "bg-red-500",    chip: "bg-red-500/20 text-red-300 ring-red-500/40",       label: "VIG" },
  spirit:  { dot: "bg-amber-400",  chip: "bg-amber-400/20 text-amber-200 ring-amber-400/40", label: "SPI" },
  mind:    { dot: "bg-sky-400",    chip: "bg-sky-400/20 text-sky-200 ring-sky-400/40",       label: "MND" },
  blood:   { dot: "bg-fuchsia-500", chip: "bg-fuchsia-500/20 text-fuchsia-200 ring-fuchsia-500/40", label: "BLD" },
  generic: { dot: "bg-slate-400",  chip: "bg-slate-400/20 text-slate-200 ring-slate-400/40", label: "GEN" },
};

const ESSENCE_ORDER: Essence[] = ["vigor", "spirit", "mind", "blood"];

// Suggested per-turn budget — purely cosmetic until the server enforces a
// timer. Resets when `state.turn` changes.
const TURN_TIMER_SECONDS = 60;

interface FloatingNumber {
  id: number;
  target: string;
  value: number;
  kind: "damage" | "heal";
  tick?: string;
}

// --------------------------------------------------------------------------- //
// Page                                                                        //
// --------------------------------------------------------------------------- //

export function BattlePage() {
  const params = useParams<{ matchId?: string }>();
  const [matchId, setMatchId] = useState<string | null>(params.matchId ?? null);
  const [state, setState] = useState<MatchState | null>(null);
  const [events, setEvents] = useState<MatchEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [queue, setQueue] = useState<QueuedAction[]>([]);
  const [pending, setPending] = useState<{
    character_id: string;
    skill: Skill;
    paid: Partial<Record<Essence, number>>;
  } | null>(null);
  const [floats, setFloats] = useState<FloatingNumber[]>([]);
  const [turnStartedAt, setTurnStartedAt] = useState<number>(() => Date.now());
  const [now, setNow] = useState<number>(() => Date.now());
  const wsRef = useRef<WebSocket | null>(null);
  const floatId = useRef(0);

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

  useEffect(() => () => wsRef.current?.close(), []);

  // 1-second cadence is enough for a smooth-looking timer bar.
  useEffect(() => {
    const handle = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(handle);
  }, []);

  // Reset the local turn timer whenever the server advances the turn.
  useEffect(() => {
    if (!state) return;
    setTurnStartedAt(Date.now());
  }, [state?.turn, state?.current_side]);

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    // Drop floats after the animation finishes so the array doesn't grow.
    window.setTimeout(() => {
      const ids = new Set(additions.map((f) => f.id));
      setFloats((prev) => prev.filter((f) => !ids.has(f.id)));
    }, 1400);
  };

  const connect = (id: string) => {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const token = auth.getToken();
    const url = new URL(`${proto}//${window.location.host}/api/match/ws/${id}`);
    if (token) url.searchParams.set("token", token);
    const ws = new WebSocket(url.toString());
    ws.onmessage = (msg) => {
      const frame = JSON.parse(msg.data);
      if (frame.type === "state") {
        setState(frame.state);
        setQueue([]);  // server resolved a turn — local queue is stale
        setPending(null);
        if (Array.isArray(frame.events)) {
          setEvents((prev) => [...prev, ...frame.events]);
          spawnFloats(frame.events as MatchEvent[]);
        }
      } else if (frame.type === "error") {
        setError(frame.detail);
      }
    };
    ws.onerror = () => setError("WebSocket error");
    wsRef.current = ws;
  };

  const submitTurn = () => {
    wsRef.current?.send(
      JSON.stringify({
        type: "actions",
        actions: queue,
      }),
    );
  };

  if (!state) {
    return (
      <div className="p-8">
        <h2 className="mb-4 text-2xl font-bold">Battle (demo)</h2>
        <p className="mb-4 text-sm text-slate-400">
          Spawns a match between {DEMO_TEAM_A.join("/")} and {DEMO_TEAM_B.join("/")} on Olympus.
        </p>
        <button
          type="button"
          onClick={startMatch}
          className="rounded-md bg-emerald-600 px-4 py-2 font-medium hover:bg-emerald-500"
        >
          Start match
        </button>
        {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
      </div>
    );
  }

  // The bottom team is always the one whose turn it is — gives the player
  // the "I command this side" framing that arena games use.
  const activePlayer = state.current_side === "A" ? state.a : state.b;
  const opponent = state.current_side === "A" ? state.b : state.a;

  const remainingPool = queue.reduce(
    (pool, action) => subtractPayment(pool, action.paid),
    activePlayer.essences,
  );

  const charactersAlreadyActing = new Set(queue.map((a) => a.character_id));

  const enqueue = (action: QueuedAction) => {
    setQueue((prev) => [...prev, action]);
    setPending(null);
  };

  const onSkillClick = (character: CharacterState, skill: Skill) => {
    const paid = computePayment(skill.cost, remainingPool);
    if (paid === null) return;
    if (skill.target === "self") {
      enqueue({
        character_id: character.id,
        skill_id: skill.id,
        target_ids: [character.id],
        paid,
      });
      return;
    }
    if (!needsTargetPick(skill.target)) {
      enqueue({
        character_id: character.id,
        skill_id: skill.id,
        target_ids: [],
        paid,
      });
      return;
    }
    setPending({ character_id: character.id, skill, paid });
  };

  const onTargetClick = (targetId: string) => {
    if (!pending) return;
    enqueue({
      character_id: pending.character_id,
      skill_id: pending.skill.id,
      target_ids: [targetId],
      paid: pending.paid,
    });
  };

  const validTargetIds = pending
    ? targetCandidates(pending.skill, activePlayer, opponent).map((c) => c.id)
    : null;

  const elapsedMs = state.finished ? 0 : Math.max(0, now - turnStartedAt);
  const timerRatio = state.finished
    ? 0
    : Math.max(0, 1 - elapsedMs / (TURN_TIMER_SECONDS * 1000));
  const secondsLeft = state.finished ? 0 : Math.max(0, Math.ceil(TURN_TIMER_SECONDS - elapsedMs / 1000));

  return (
    <div className="mx-auto flex min-h-screen max-w-5xl flex-col gap-4 px-4 py-6">
      {/* HUD ──────────────────────────────────────────────────────────────── */}
      <header className="overflow-hidden rounded-xl bg-slate-900/80 shadow ring-1 ring-slate-800">
        <div className="flex items-center justify-between px-5 py-3">
          <div className="text-sm text-slate-400">
            <span className="font-mono text-slate-500">match {matchId?.slice(0, 8)}</span>
            <span className="mx-2 text-slate-700">·</span>
            <span>arena {state.arena_id}</span>
          </div>
          <div className="text-center">
            <div className="text-xs uppercase tracking-wider text-slate-500">Turn</div>
            <div className="text-2xl font-bold tabular-nums">{state.turn}</div>
          </div>
          <div className="text-right text-sm">
            <div className="text-xs uppercase tracking-wider text-slate-500">
              Acting · {secondsLeft}s
            </div>
            <div
              className={
                state.current_side === "A"
                  ? "font-bold text-emerald-400"
                  : "font-bold text-rose-400"
              }
            >
              Side {state.current_side}
            </div>
          </div>
        </div>
        {!state.finished && (
          <div className="h-1 bg-slate-800">
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

      {/* OPPONENT (top) ──────────────────────────────────────────────────── */}
      <section
        aria-label="Opponent team"
        className="rounded-xl bg-gradient-to-b from-slate-900/80 to-slate-900/30 p-4 ring-1 ring-slate-800"
      >
        <SideHeader
          label={`Opponent · Side ${opponent.side}`}
          essences={opponent.essences}
          tone="rose"
        />
        <div className="mt-3 grid grid-cols-3 gap-3">
          {opponent.characters.map((c) => (
            <CharacterPortrait
              key={c.id}
              character={c}
              isOpponent
              clickable={pending?.skill.target === "single_enemy"}
              highlighted={validTargetIds?.includes(c.id) ?? false}
              floats={floatsByTarget.get(c.id) ?? []}
              onClick={() => onTargetClick(c.id)}
            />
          ))}
        </div>
      </section>

      {/* CENTER BAND — chakra/essence pool ──────────────────────────────── */}
      <section className="flex items-center justify-between rounded-xl bg-slate-900/80 px-5 py-3 shadow-inner ring-1 ring-slate-800">
        <span className="text-xs uppercase tracking-wider text-slate-500">Essence pool</span>
        <EssenceBar pool={remainingPool} large />
        <span className="text-xs text-slate-500">
          {queue.length === 0
            ? "no actions queued"
            : `${queue.length}/3 queued`}
        </span>
      </section>

      {/* PLAYER (bottom) ─────────────────────────────────────────────────── */}
      <section
        aria-label="Your team"
        className="rounded-xl bg-gradient-to-t from-slate-900/80 to-slate-900/30 p-4 ring-1 ring-slate-800"
      >
        <SideHeader
          label={`You · Side ${activePlayer.side}`}
          essences={activePlayer.essences}
          tone="emerald"
        />
        <div className="mt-3 grid grid-cols-3 gap-3">
          {activePlayer.characters.map((c) => (
            <CharacterPortrait
              key={c.id}
              character={c}
              clickable={pending?.skill.target === "single_ally"}
              highlighted={validTargetIds?.includes(c.id) ?? false}
              queued={charactersAlreadyActing.has(c.id)}
              floats={floatsByTarget.get(c.id) ?? []}
              onClick={() => onTargetClick(c.id)}
            />
          ))}
        </div>

        {/* Skill rows aligned under each character ──────────────────────── */}
        {!state.finished && (
          <div className="mt-4 grid grid-cols-3 gap-3">
            {activePlayer.characters.map((character) => {
              const def = charById.get(character.id);
              const stunned = character.statuses.some((s) => s.name === "stun");
              const acting = charactersAlreadyActing.has(character.id);
              const dead = character.hp <= 0;
              return (
                <SkillStack
                  key={character.id}
                  character={character}
                  def={def}
                  disabledReason={
                    dead ? "down" : stunned ? "stunned" : acting ? "queued" : null
                  }
                  remainingPool={remainingPool}
                  onSkillClick={onSkillClick}
                />
              );
            })}
          </div>
        )}
      </section>

      {/* TARGET PROMPT ───────────────────────────────────────────────────── */}
      {pending && (
        <div className="rounded-xl bg-amber-500/10 px-4 py-3 text-sm text-amber-200 ring-1 ring-amber-500/40">
          Pick a target for{" "}
          <span className="font-semibold">{pending.skill.name}</span> — click a glowing portrait above.
          <button
            type="button"
            onClick={() => setPending(null)}
            className="ml-3 rounded border border-amber-500/40 px-2 py-0.5 text-xs hover:bg-amber-500/20"
          >
            cancel
          </button>
        </div>
      )}

      {/* ACTION QUEUE ────────────────────────────────────────────────────── */}
      {!state.finished && (
        <section className="rounded-xl bg-slate-900/80 p-4 ring-1 ring-slate-800">
          <ActionQueue
            queue={queue}
            charById={charById}
            onRemove={(idx) => setQueue((prev) => prev.filter((_, i) => i !== idx))}
          />
          <div className="mt-3 flex gap-3">
            <button
              type="button"
              onClick={submitTurn}
              disabled={queue.length === 0}
              className="rounded-md bg-blue-600 px-5 py-2 font-medium hover:bg-blue-500 disabled:opacity-40"
            >
              Confirm turn
            </button>
            <button
              type="button"
              onClick={() => setQueue([])}
              disabled={queue.length === 0}
              className="rounded-md bg-slate-700 px-4 py-2 text-sm hover:bg-slate-600 disabled:opacity-40"
            >
              Clear queue
            </button>
          </div>
        </section>
      )}

      {state.finished && (
        <p className="rounded-xl bg-slate-900/80 px-5 py-4 text-lg font-semibold ring-1 ring-slate-800">
          Match finished — winner: {state.winner ?? "draw"}
        </p>
      )}

      {/* EVENT LOG ──────────────────────────────────────────────────────── */}
      <details className="rounded-xl bg-slate-900/80 px-4 py-3 text-sm ring-1 ring-slate-800">
        <summary className="cursor-pointer text-xs font-semibold uppercase text-slate-400">
          Event log ({events.length})
        </summary>
        <ul className="mt-2 max-h-60 space-y-1 overflow-y-auto rounded-md bg-slate-950 p-3 text-xs font-mono">
          {events.slice(-50).map((e, i) => (
            <li key={i}>
              <span className="text-emerald-400">{e.kind}</span>{" "}
              <span className="text-slate-500">{JSON.stringify(e.details)}</span>
            </li>
          ))}
        </ul>
      </details>

      {error && <p className="text-sm text-red-400">{error}</p>}
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Sub-components                                                              //
// --------------------------------------------------------------------------- //

function SideHeader({
  label,
  essences,
  tone,
}: {
  label: string;
  essences: Partial<Record<Essence, number>>;
  tone: "emerald" | "rose";
}) {
  const dot = tone === "emerald" ? "bg-emerald-400" : "bg-rose-400";
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
        <span className={`inline-block h-2 w-2 rounded-full ${dot}`} />
        {label}
      </div>
      <EssenceBar pool={essences} animated />
    </div>
  );
}

function EssenceBar({
  pool,
  large = false,
  animated = false,
}: {
  pool: Partial<Record<Essence, number>>;
  large?: boolean;
  animated?: boolean;
}) {
  const items = ESSENCE_ORDER.filter((k) => (pool[k] ?? 0) > 0);
  if (items.length === 0) {
    return <span className="text-xs italic text-slate-600">empty</span>;
  }
  return (
    <div className={`flex items-center gap-2 ${large ? "text-base" : "text-xs"}`}>
      {items.map((k) => {
        const style = ESSENCE_STYLE[k];
        const count = pool[k]!;
        const className = `inline-flex items-center gap-1 rounded-full px-2 py-0.5 ring-1 ${style.chip}`;
        const inner = (
          <>
            <span className={`inline-block h-2 w-2 rounded-full ${style.dot}`} />
            <span className="font-mono font-semibold">{count}</span>
            <span className="opacity-70">{style.label}</span>
          </>
        );
        // Re-keying by count makes framer-motion replay the entrance whenever
        // the server pushes a new pool — reads like "chakra rolled in".
        if (animated) {
          return (
            <motion.span
              key={`${k}-${count}`}
              initial={{ scale: 0.4, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: "spring", stiffness: 420, damping: 20 }}
              className={className}
              title={k}
            >
              {inner}
            </motion.span>
          );
        }
        return (
          <span key={k} className={className} title={k}>
            {inner}
          </span>
        );
      })}
    </div>
  );
}

function CharacterPortrait({
  character,
  isOpponent = false,
  clickable = false,
  highlighted = false,
  queued = false,
  floats = [],
  onClick,
}: {
  character: CharacterState;
  isOpponent?: boolean;
  clickable?: boolean;
  highlighted?: boolean;
  queued?: boolean;
  floats?: FloatingNumber[];
  onClick?: () => void;
}) {
  const dead = character.hp <= 0;
  const ratio = character.hp_max > 0 ? character.hp / character.hp_max : 0;
  const hpColor = ratio > 0.6 ? "bg-emerald-500" : ratio > 0.3 ? "bg-amber-400" : "bg-red-500";

  // First letter as a portrait stand-in until we wire real art.
  const initial = character.name.charAt(0).toUpperCase();
  const interactive = clickable && highlighted && !dead;

  const handle = interactive ? onClick : undefined;

  // Shake whenever a new damage float arrives for this character.
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
      role={interactive ? "button" : undefined}
      onClick={handle}
      className={[
        "relative rounded-lg p-3 ring-1 transition",
        dead ? "bg-slate-950/60 ring-slate-900 opacity-50" : "bg-slate-800 ring-slate-700",
        interactive ? "cursor-pointer ring-amber-400 ring-2 hover:bg-slate-700" : "",
        queued ? "ring-emerald-500/70 ring-2" : "",
      ].join(" ")}
    >
      <FloatingNumbers items={floats} />
      <div className="flex items-center gap-3">
        <div
          className={[
            "flex h-12 w-12 shrink-0 items-center justify-center rounded-md text-xl font-bold",
            isOpponent ? "bg-rose-900/60 text-rose-200" : "bg-emerald-900/60 text-emerald-200",
            dead ? "grayscale" : "",
          ].join(" ")}
        >
          {initial}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-1">
            <span className="truncate text-sm font-semibold">{character.name}</span>
            <span className="font-mono text-xs tabular-nums text-slate-300">
              {character.hp}/{character.hp_max}
            </span>
          </div>
          <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-900">
            <div
              className={`h-full transition-all ${hpColor}`}
              style={{ width: `${Math.max(0, Math.min(100, ratio * 100))}%` }}
            />
          </div>
          {character.shield > 0 && (
            <div className="mt-1 text-[10px] font-semibold text-cyan-300">
              + shield {character.shield}
            </div>
          )}
        </div>
      </div>

      {character.statuses.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {character.statuses.map((s, i) => (
            <span
              key={i}
              className="rounded bg-slate-900/70 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-slate-300 ring-1 ring-slate-700"
              title={`${s.name} (${s.duration}t · ${s.value})`}
            >
              {s.name}
              <span className="ml-1 text-slate-500">{s.duration}</span>
            </span>
          ))}
        </div>
      )}

      {dead && (
        <div className="absolute inset-0 grid place-items-center bg-slate-950/40 text-xs font-bold uppercase tracking-widest text-red-400">
          KO
        </div>
      )}
    </motion.div>
  );
}

function SkillStack({
  character,
  def,
  disabledReason,
  remainingPool,
  onSkillClick,
}: {
  character: CharacterState;
  def: Character | undefined;
  disabledReason: string | null;
  remainingPool: Partial<Record<Essence, number>>;
  onSkillClick: (character: CharacterState, skill: Skill) => void;
}) {
  if (!def) {
    return <div className="rounded-lg bg-slate-900/40 p-2 text-xs text-slate-600">…</div>;
  }
  return (
    <div className="rounded-lg bg-slate-900/60 p-2 ring-1 ring-slate-800">
      {disabledReason && (
        <div className="mb-1 text-center text-[10px] font-semibold uppercase tracking-wider text-amber-400">
          {disabledReason}
        </div>
      )}
      <div className="flex flex-col gap-1.5">
        {def.skills.map((skill) => {
          const cd = character.cooldowns[skill.id] ?? 0;
          const affordable = computePayment(skill.cost, remainingPool) !== null;
          const disabled = !!disabledReason || cd > 0 || !affordable;
          return (
            <button
              key={skill.id}
              type="button"
              onClick={() => onSkillClick(character, skill)}
              disabled={disabled}
              className={[
                "group flex items-center justify-between rounded-md px-2 py-1.5 text-left text-xs transition",
                disabled
                  ? "bg-slate-900/60 text-slate-500"
                  : "bg-slate-800 text-slate-100 hover:bg-slate-700 ring-1 ring-slate-700",
              ].join(" ")}
              title={describeSkill(skill)}
            >
              <span className="truncate font-medium">{skill.name}</span>
              <span className="ml-2 flex shrink-0 items-center gap-1">
                {cd > 0 ? (
                  <span className="rounded bg-slate-950 px-1 font-mono text-[10px] text-amber-300">
                    {cd}
                  </span>
                ) : (
                  <CostPips cost={skill.cost} />
                )}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function CostPips({ cost }: { cost: Partial<Record<Essence, number>> }) {
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
    return <span className="text-[10px] italic text-slate-500">free</span>;
  }
  return (
    <span className="flex items-center gap-0.5">
      {pips.map((p) => (
        <span key={p.key} className={`inline-block h-2 w-2 rounded-full ${p.color}`} />
      ))}
    </span>
  );
}

function ActionQueue({
  queue,
  charById,
  onRemove,
}: {
  queue: QueuedAction[];
  charById: Map<string, Character>;
  onRemove: (idx: number) => void;
}) {
  if (queue.length === 0) {
    return <p className="text-xs italic text-slate-500">No actions queued.</p>;
  }
  return (
    <ol className="flex flex-wrap gap-2">
      {queue.map((action, i) => {
        const def = charById.get(action.character_id);
        const skill = def?.skills.find((s) => s.id === action.skill_id);
        return (
          <li
            key={i}
            className="flex items-center gap-2 rounded-full bg-slate-800 px-3 py-1 text-xs ring-1 ring-slate-700"
          >
            <span className="font-semibold">{def?.name ?? action.character_id}</span>
            <span className="text-slate-400">→</span>
            <span>{skill?.name ?? action.skill_id}</span>
            {action.target_ids.length > 0 && (
              <span className="text-slate-500">@ {action.target_ids.join(", ")}</span>
            )}
            <button
              type="button"
              onClick={() => onRemove(i)}
              className="ml-1 text-rose-400 hover:text-rose-300"
              aria-label="remove"
            >
              ×
            </button>
          </li>
        );
      })}
    </ol>
  );
}

function FloatingNumbers({ items }: { items: FloatingNumber[] }) {
  return (
    <div className="pointer-events-none absolute inset-x-0 top-0 z-10 flex justify-center">
      <AnimatePresence>
        {items.map((f) => (
          <motion.span
            key={f.id}
            initial={{ y: 0, opacity: 0, scale: 0.7 }}
            animate={{ y: -36, opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 1.2, ease: "easeOut" }}
            className={[
              "absolute select-none text-lg font-extrabold drop-shadow",
              f.kind === "damage" ? "text-red-400" : "text-emerald-300",
            ].join(" ")}
          >
            {f.kind === "damage" ? "-" : "+"}
            {f.value}
            {f.tick && (
              <span className="ml-1 align-middle text-[10px] uppercase opacity-80">
                {f.tick}
              </span>
            )}
          </motion.span>
        ))}
      </AnimatePresence>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Helpers                                                                     //
// --------------------------------------------------------------------------- //

function targetCandidates(
  skill: Skill,
  active: PlayerState,
  opponent: PlayerState,
): CharacterState[] {
  const pool = skill.target === "single_enemy" ? opponent : active;
  return pool.characters.filter((c) => c.hp > 0);
}

function describeSkill(skill: Skill): string {
  const cost = Object.entries(skill.cost)
    .filter(([, v]) => (v ?? 0) > 0)
    .map(([k, v]) => `${v}${k[0]}`)
    .join("+") || "free";
  return `${skill.name} · ${cost} · CD ${skill.cooldown} · ${skill.target}`;
}
