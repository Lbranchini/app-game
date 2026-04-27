import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api, auth } from "@/api/client";
import { draftApi, type DraftState, type Side } from "@/api/draft";
import type { Character } from "@/types/api";

/**
 * Two modes:
 *
 * 1. `/draft` — single-driver dev mode. The operator clicks bans and picks for
 *    both sides; useful when matchmaking is bypassed.
 * 2. `/draft/:draftId?side=A` — live multiplayer. Subscribes to the draft
 *    WebSocket and only enables interactions for the user's own side. Routed
 *    here from `/matchmaking` once the server pairs two players.
 */
export function DraftPage() {
  const navigate = useNavigate();
  const params = useParams<{ draftId?: string }>();
  const [searchParams] = useSearchParams();
  const querySide = searchParams.get("side") as Side | null;
  const liveMode = Boolean(params.draftId);

  const characters = useQuery({ queryKey: ["characters"], queryFn: api.listCharacters });
  const arenas = useQuery({ queryKey: ["arenas"], queryFn: api.listArenas });
  const me = useQuery({ queryKey: ["me"], queryFn: api.me });
  const unlockedSet = useMemo(() => {
    const list = me.data?.player?.unlocked_characters;
    return list ? new Set(list) : null; // null = roster filter not applicable yet
  }, [me.data]);

  const [arenaId, setArenaId] = useState<string>("olympus");
  const [draft, setDraft] = useState<DraftState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // --- live-mode subscription ---------------------------------------------
  useEffect(() => {
    if (!liveMode || !params.draftId) return;
    const token = auth.getToken();
    if (!token) {
      setError("Not authenticated.");
      return;
    }
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(
      `${proto}//${window.location.host}/api/draft/ws/${params.draftId}?token=${encodeURIComponent(token)}`,
    );
    ws.onmessage = (msg) => {
      const frame = JSON.parse(msg.data);
      if (frame.type === "state") {
        setDraft(frame.draft);
        if (frame.match_id) {
          ws.close();
          navigate(`/battle/${frame.match_id}`);
        }
      }
    };
    ws.onerror = () => setError("WebSocket error.");
    wsRef.current = ws;
    return () => ws.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [liveMode, params.draftId]);

  // --- single-driver dev mode --------------------------------------------
  const start = async () => {
    try {
      setError(null);
      setDraft(
        await draftApi.start({
          side_a_player_id: "you",
          side_b_player_id: "opponent",
          arena_id: arenaId,
        }),
      );
    } catch (e) {
      setError(String(e));
    }
  };

  const ban = async (side: Side, characterId: string) => {
    if (!draft) return;
    try {
      const next = await draftApi.ban(draft.draft_id, side, characterId);
      if (!liveMode) setDraft(next); // live mode receives via WS
    } catch (e) {
      setError(String(e));
    }
  };

  const pick = async (side: Side, characterId: string) => {
    if (!draft) return;
    try {
      const next = await draftApi.pick(draft.draft_id, side, characterId);
      if (!liveMode) setDraft(next);
    } catch (e) {
      setError(String(e));
    }
  };

  // Auto-finalize when both players are done picking.
  useEffect(() => {
    if (!draft || draft.phase !== "confirm") return;
    // In live mode only one side should drive finalize — the higher of the two ids.
    if (liveMode && querySide !== "A") return;
    (async () => {
      try {
        const result = await draftApi.finalize(draft.draft_id);
        if (!liveMode) navigate(`/battle/${result.match_id}`);
        // In live mode the WS will deliver match_id; navigation happens there.
      } catch (e) {
        setError(String(e));
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft?.phase]);

  // --- render -------------------------------------------------------------
  if (characters.isLoading || arenas.isLoading) {
    return <p className="p-8">Loading…</p>;
  }
  if (!characters.data || !arenas.data) {
    return <p className="p-8 text-red-400">Catalog failed to load.</p>;
  }

  if (!liveMode && !draft) {
    return (
      <div className="p-8">
        <h2 className="mb-4 text-2xl font-bold">Ranked Draft (dev mode)</h2>
        <p className="mb-4 text-sm text-slate-400">
          Drives both sides locally. For multiplayer use{" "}
          <a className="text-emerald-400 underline" href="/matchmaking">
            /matchmaking
          </a>
          .
        </p>
        <label className="mb-3 block text-sm text-slate-400">Arena:</label>
        <select
          value={arenaId}
          onChange={(e) => setArenaId(e.target.value)}
          className="mb-6 w-full max-w-sm rounded-md bg-slate-800 p-2 text-slate-100"
        >
          {arenas.data.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={start}
          className="rounded-md bg-emerald-600 px-4 py-2 font-medium hover:bg-emerald-500"
        >
          Start draft
        </button>
        {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
      </div>
    );
  }

  if (!draft) {
    return <p className="p-8">Connecting to draft…</p>;
  }

  const arena = arenas.data.find((a) => a.id === draft.arena_id);
  const banned = Object.values(draft.bans).filter((v): v is string => v !== null);
  const picked = [...draft.picks.A, ...draft.picks.B];
  const unavailable = new Set([...banned, ...picked]);

  /** Whose turn is it to take the next action? */
  const expectedSide: Side | null =
    draft.phase === "ban"
      ? draft.bans.A === null
        ? "A"
        : draft.bans.B === null
        ? "B"
        : null
      : draft.phase === "pick"
      ? draft.pick_order[draft.pick_index] ?? null
      : null;

  /** In live mode you can only act when it's your side AND your turn. */
  const canAct = !liveMode || (querySide !== null && expectedSide === querySide);

  const onCharacterClick = (characterId: string) => {
    if (!canAct || unavailable.has(characterId) || expectedSide === null) return;
    if (draft.phase === "ban") {
      ban(expectedSide, characterId);
    } else if (draft.phase === "pick") {
      pick(expectedSide, characterId);
    }
  };

  return (
    <div className="p-8">
      <header className="mb-6">
        <h2 className="text-2xl font-bold">
          Draft {liveMode && querySide && `— you are side ${querySide}`}
        </h2>
        <p className="text-sm text-slate-400">
          Arena <span className="font-semibold">{arena?.name ?? draft.arena_id}</span>{" "}
          {arena?.description && <span className="ml-2 italic">— {arena.description}</span>}
        </p>
        <p className="mt-2 text-sm">
          Phase: <span className="font-semibold uppercase">{draft.phase}</span>
          {expectedSide && (
            <>
              {" "}
              · Now acting:{" "}
              <span className={canAct ? "font-semibold text-emerald-400" : "font-semibold"}>
                side {expectedSide}
                {canAct && " (you)"}
              </span>
            </>
          )}
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        <SideSummary title="Side A" ban={draft.bans.A} picks={draft.picks.A} />
        <SideSummary title="Side B" ban={draft.bans.B} picks={draft.picks.B} />
      </div>

      <h3 className="mt-8 mb-3 text-sm font-semibold uppercase text-slate-400">
        Pool
        {liveMode && unlockedSet && (
          <span className="ml-2 font-normal text-slate-500">
            (locked picks are greyed out)
          </span>
        )}
      </h3>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {characters.data.map((c) => {
          // Roster filter only applies when this client owns the next pick.
          const isPick = draft.phase === "pick";
          const lockedForMe =
            liveMode && unlockedSet !== null && !unlockedSet.has(c.id) && isPick;
          return (
            <CharacterTile
              key={c.id}
              character={c}
              disabled={
                !canAct ||
                unavailable.has(c.id) ||
                lockedForMe ||
                draft.phase === "done" ||
                draft.phase === "cancelled" ||
                draft.phase === "confirm"
              }
              highlight={
                draft.bans.A === c.id || draft.bans.B === c.id
                  ? "banned"
                  : draft.picks.A.includes(c.id)
                  ? "team_a"
                  : draft.picks.B.includes(c.id)
                  ? "team_b"
                  : lockedForMe
                  ? "locked"
                  : null
              }
              onClick={() => onCharacterClick(c.id)}
            />
          );
        })}
      </div>

      {draft.phase === "confirm" && (
        <p className="mt-6 text-emerald-400">Draft complete. Starting match…</p>
      )}
      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
    </div>
  );
}

function SideSummary({
  title,
  ban,
  picks,
}: {
  title: string;
  ban: string | null;
  picks: string[];
}) {
  return (
    <div className="rounded-xl bg-slate-800 p-4">
      <h3 className="mb-2 text-lg font-bold">{title}</h3>
      <p className="text-sm text-slate-400">
        Ban: <span className="text-slate-200">{ban ?? "—"}</span>
      </p>
      <p className="mt-1 text-sm text-slate-400">
        Picks: <span className="text-slate-200">{picks.join(", ") || "—"}</span>
      </p>
    </div>
  );
}

function CharacterTile({
  character,
  disabled,
  highlight,
  onClick,
}: {
  character: Character;
  disabled: boolean;
  highlight: "banned" | "team_a" | "team_b" | "locked" | null;
  onClick: () => void;
}) {
  const colors = {
    banned: "bg-red-900/40 line-through opacity-60",
    team_a: "bg-blue-900/40 ring-1 ring-blue-500",
    team_b: "bg-amber-900/40 ring-1 ring-amber-500",
    locked: "bg-slate-900 opacity-30",
  } as const;
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`rounded-lg p-3 text-left transition ${
        highlight ? colors[highlight] : "bg-slate-800 hover:bg-slate-700"
      } ${disabled && !highlight ? "cursor-not-allowed opacity-40" : ""}`}
    >
      <div className="flex items-baseline justify-between">
        <span className="font-semibold">{character.name}</span>
        <span className="text-xs uppercase text-slate-400">{character.mythology}</span>
      </div>
      <p className="text-xs text-slate-500">
        HP {character.base_hp} • {character.archetype.replace("_", " ")}
      </p>
    </button>
  );
}
