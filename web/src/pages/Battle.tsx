import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
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
  const wsRef = useRef<WebSocket | null>(null);

  const characters = useQuery({ queryKey: ["characters"], queryFn: api.listCharacters });
  const charById = useMemo(() => {
    const map = new Map<string, Character>();
    (characters.data ?? []).forEach((c) => map.set(c.id, c));
    return map;
  }, [characters.data]);

  useEffect(() => () => wsRef.current?.close(), []);

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

  const connect = (id: string) => {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${proto}//${window.location.host}/api/match/ws/${id}`);
    ws.onmessage = (msg) => {
      const frame = JSON.parse(msg.data);
      if (frame.type === "state") {
        setState(frame.state);
        setQueue([]);  // server resolved a turn — local queue is stale
        setPending(null);
        if (Array.isArray(frame.events)) {
          setEvents((prev) => [...prev, ...frame.events]);
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

  const activePlayer = state.current_side === "A" ? state.a : state.b;
  const opponent = state.current_side === "A" ? state.b : state.a;

  // The pool the operator sees already accounts for what's been queued.
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
    if (paid === null) return; // shouldn't happen because button is disabled
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

  return (
    <div className="p-8">
      <header className="mb-6 flex items-baseline justify-between">
        <h2 className="text-2xl font-bold">Match {matchId?.slice(0, 8)}…</h2>
        <span className="text-sm text-slate-400">
          Turn {state.turn} • Active: side {state.current_side} • Arena: {state.arena_id}
        </span>
      </header>

      <div className="grid gap-6 md:grid-cols-2">
        <Team title="Side A" player={state.a} />
        <Team title="Side B" player={state.b} />
      </div>

      {!state.finished && (
        <div className="mt-8 rounded-xl bg-slate-800 p-5">
          <div className="mb-3 flex items-baseline justify-between">
            <h3 className="text-lg font-semibold">Plan turn — side {state.current_side}</h3>
            <span className="text-xs text-slate-400">
              Pool after queue:{" "}
              {Object.entries(remainingPool)
                .filter(([, v]) => (v ?? 0) > 0)
                .map(([k, v]) => `${k.slice(0, 3)}=${v}`)
                .join(" · ") || "—"}
            </span>
          </div>

          {pending ? (
            <TargetPicker
              skill={pending.skill}
              opponent={opponent}
              active={activePlayer}
              onPick={onTargetClick}
              onCancel={() => setPending(null)}
            />
          ) : (
            <SkillBoard
              activePlayer={activePlayer}
              charById={charById}
              charactersAlreadyActing={charactersAlreadyActing}
              remainingPool={remainingPool}
              onSkillClick={onSkillClick}
            />
          )}

          <ActionQueue
            queue={queue}
            onRemove={(idx) => setQueue((prev) => prev.filter((_, i) => i !== idx))}
          />

          <div className="mt-4 flex gap-3">
            <button
              type="button"
              onClick={submitTurn}
              className="rounded-md bg-blue-600 px-4 py-2 font-medium hover:bg-blue-500"
            >
              Confirm turn ({queue.length})
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
        </div>
      )}

      {state.finished && (
        <p className="mt-6 text-lg font-semibold">
          Match finished — winner: {state.winner ?? "draw"}
        </p>
      )}

      <div className="mt-8">
        <h3 className="mb-2 text-sm font-semibold uppercase text-slate-400">Event log</h3>
        <ul className="max-h-60 space-y-1 overflow-y-auto rounded-md bg-slate-900 p-3 text-xs font-mono">
          {events.slice(-30).map((e, i) => (
            <li key={i}>
              <span className="text-emerald-400">{e.kind}</span>{" "}
              <span className="text-slate-500">{JSON.stringify(e.details)}</span>
            </li>
          ))}
        </ul>
      </div>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Sub-components                                                              //
// --------------------------------------------------------------------------- //

function Team({ title, player }: { title: string; player: PlayerState }) {
  return (
    <div className="rounded-xl bg-slate-800 p-5">
      <h3 className="mb-3 text-lg font-bold">{title}</h3>
      <ul className="space-y-2">
        {player.characters.map((c) => (
          <li key={c.id} className="rounded bg-slate-900 p-3">
            <div className="flex justify-between text-sm">
              <span className="font-medium">{c.name}</span>
              <span className={c.hp <= 0 ? "text-red-500" : "text-slate-300"}>
                {c.hp}/{c.hp_max}
                {c.shield > 0 && <span className="ml-1 text-cyan-400">+{c.shield}</span>}
              </span>
            </div>
            {c.statuses.length > 0 && (
              <p className="mt-1 text-xs text-slate-500">
                {c.statuses.map((s) => `${s.name}(${s.duration})`).join(" · ")}
              </p>
            )}
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-slate-500">
        Essences:{" "}
        {Object.entries(player.essences)
          .filter(([, v]) => (v ?? 0) > 0)
          .map(([k, v]) => `${k.slice(0, 3)}=${v}`)
          .join(", ") || "—"}
      </p>
    </div>
  );
}

function SkillBoard({
  activePlayer,
  charById,
  charactersAlreadyActing,
  remainingPool,
  onSkillClick,
}: {
  activePlayer: PlayerState;
  charById: Map<string, Character>;
  charactersAlreadyActing: Set<string>;
  remainingPool: Partial<Record<Essence, number>>;
  onSkillClick: (character: CharacterState, skill: Skill) => void;
}) {
  return (
    <div className="space-y-4">
      {activePlayer.characters
        .filter((c) => c.hp > 0)
        .map((character) => {
          const def = charById.get(character.id);
          if (!def) return null;
          const stunned = character.statuses.some((s) => s.name === "stun");
          const acting = charactersAlreadyActing.has(character.id);
          return (
            <div key={character.id} className="rounded bg-slate-900 p-3">
              <div className="mb-2 flex items-baseline justify-between">
                <span className="font-medium">{character.name}</span>
                {stunned && <span className="text-xs text-amber-400">stunned</span>}
                {acting && <span className="text-xs text-emerald-400">queued</span>}
              </div>
              <div className="flex flex-wrap gap-2">
                {def.skills.map((skill) => {
                  const cd = character.cooldowns[skill.id] ?? 0;
                  const affordable = computePayment(skill.cost, remainingPool) !== null;
                  const disabled = stunned || acting || cd > 0 || !affordable;
                  return (
                    <button
                      key={skill.id}
                      type="button"
                      onClick={() => onSkillClick(character, skill)}
                      disabled={disabled}
                      className="rounded-md bg-slate-700 px-3 py-1.5 text-sm hover:bg-slate-600 disabled:opacity-30"
                      title={`Cost: ${formatCost(skill.cost)} · CD ${skill.cooldown} · ${skill.target}`}
                    >
                      <span className="font-medium">{skill.name}</span>
                      <span className="ml-2 text-xs text-slate-400">
                        {formatCost(skill.cost)}
                        {cd > 0 && ` · CD ${cd}`}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
    </div>
  );
}

function TargetPicker({
  skill,
  active,
  opponent,
  onPick,
  onCancel,
}: {
  skill: Skill;
  active: PlayerState;
  opponent: PlayerState;
  onPick: (id: string) => void;
  onCancel: () => void;
}) {
  const pool = skill.target === "single_enemy" ? opponent : active;
  const candidates = pool.characters.filter((c) => c.hp > 0);
  return (
    <div className="rounded bg-slate-900 p-4">
      <p className="mb-3 text-sm">
        Pick target for <span className="font-semibold">{skill.name}</span> (
        {skill.target.replace("_", " ")})
      </p>
      <div className="flex flex-wrap gap-2">
        {candidates.map((c) => (
          <button
            key={c.id}
            type="button"
            onClick={() => onPick(c.id)}
            className="rounded-md bg-slate-700 px-3 py-1.5 text-sm hover:bg-slate-600"
          >
            {c.name} ({c.hp}/{c.hp_max})
          </button>
        ))}
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md bg-slate-800 px-3 py-1.5 text-sm text-slate-400 hover:bg-slate-700"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

function ActionQueue({
  queue,
  onRemove,
}: {
  queue: QueuedAction[];
  onRemove: (idx: number) => void;
}) {
  if (queue.length === 0) {
    return <p className="mt-4 text-xs italic text-slate-500">Queue is empty.</p>;
  }
  return (
    <ol className="mt-4 space-y-1 text-sm">
      {queue.map((action, i) => (
        <li key={i} className="flex items-center justify-between rounded bg-slate-900 px-3 py-1.5">
          <span>
            <span className="font-medium">{action.character_id}</span>
            {" → "}
            <span className="text-slate-300">{action.skill_id}</span>
            {action.target_ids.length > 0 && (
              <span className="ml-2 text-xs text-slate-500">@ {action.target_ids.join(", ")}</span>
            )}
          </span>
          <button
            type="button"
            onClick={() => onRemove(i)}
            className="text-xs text-red-400 hover:text-red-300"
          >
            remove
          </button>
        </li>
      ))}
    </ol>
  );
}

function formatCost(cost: Partial<Record<Essence, number>>): string {
  const parts = Object.entries(cost)
    .filter(([, v]) => (v ?? 0) > 0)
    .map(([k, v]) => `${v}${k[0]}`);
  return parts.length === 0 ? "free" : parts.join("+");
}
