import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";

interface CharacterState {
  id: string;
  name: string;
  hp: number;
  hp_max: number;
  shield: number;
  statuses: { name: string; duration: number; value: number }[];
}

interface PlayerState {
  id: string;
  side: "A" | "B";
  characters: CharacterState[];
  essences: Record<string, number>;
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

export function BattlePage() {
  const params = useParams<{ matchId?: string }>();
  const [matchId, setMatchId] = useState<string | null>(params.matchId ?? null);
  const [state, setState] = useState<MatchState | null>(null);
  const [events, setEvents] = useState<MatchEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => () => wsRef.current?.close(), []);

  // If we landed here from the draft with a match id in the URL, fetch state
  // and connect immediately.
  useEffect(() => {
    if (!params.matchId) return;
    (async () => {
      try {
        const response = await fetch(`/api/match/${params.matchId}`);
        if (!response.ok) throw new Error(await response.text());
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

  const passTurn = () => {
    wsRef.current?.send(JSON.stringify({ type: "actions", actions: [] }));
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

      <div className="mt-6 flex gap-3">
        <button
          type="button"
          onClick={passTurn}
          disabled={state.finished}
          className="rounded-md bg-blue-600 px-4 py-2 font-medium hover:bg-blue-500 disabled:opacity-40"
        >
          Pass turn (no actions)
        </button>
      </div>

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
          .filter(([, v]) => v > 0)
          .map(([k, v]) => `${k.slice(0, 3)}=${v}`)
          .join(", ") || "—"}
      </p>
    </div>
  );
}
