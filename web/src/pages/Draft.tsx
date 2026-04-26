import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { draftApi, type DraftState, type Side } from "@/api/draft";
import type { Arena, Character } from "@/types/api";

/**
 * Draft page — single-driver mode.
 *
 * Same operator clicks bans and picks for both sides so the flow can be
 * tested end-to-end without matchmaking. The two-player live version uses
 * the same REST endpoints + a WebSocket fan-out (next iteration).
 */
export function DraftPage() {
  const navigate = useNavigate();
  const characters = useQuery({ queryKey: ["characters"], queryFn: api.listCharacters });
  const arenas = useQuery({ queryKey: ["arenas"], queryFn: api.listArenas });

  const [arenaId, setArenaId] = useState<string>("olympus");
  const [draft, setDraft] = useState<DraftState | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setDraft(null);
    setError(null);
  };

  const start = async () => {
    try {
      reset();
      const next = await draftApi.start({
        side_a_player_id: "you",
        side_b_player_id: "opponent",
        arena_id: arenaId,
      });
      setDraft(next);
    } catch (e) {
      setError(String(e));
    }
  };

  const ban = async (side: Side, characterId: string) => {
    if (!draft) return;
    try {
      setDraft(await draftApi.ban(draft.draft_id, side, characterId));
    } catch (e) {
      setError(String(e));
    }
  };

  const pick = async (side: Side, characterId: string) => {
    if (!draft) return;
    try {
      setDraft(await draftApi.pick(draft.draft_id, side, characterId));
    } catch (e) {
      setError(String(e));
    }
  };

  const finalize = async () => {
    if (!draft) return;
    try {
      const result = await draftApi.finalize(draft.draft_id);
      navigate(`/battle/${result.match_id}`);
    } catch (e) {
      setError(String(e));
    }
  };

  useEffect(() => {
    if (draft?.phase === "confirm") {
      finalize();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft?.phase]);

  if (characters.isLoading || arenas.isLoading) {
    return <p className="p-8">Loading…</p>;
  }
  if (!characters.data || !arenas.data) {
    return <p className="p-8 text-red-400">Catalog failed to load.</p>;
  }

  if (!draft) {
    return (
      <div className="p-8">
        <h2 className="mb-4 text-2xl font-bold">Ranked Draft</h2>
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

  const arena = arenas.data.find((a) => a.id === draft.arena_id);
  const banned = Object.values(draft.bans).filter((v): v is string => v !== null);
  const picked = [...draft.picks.A, ...draft.picks.B];
  const unavailable = new Set([...banned, ...picked]);

  const onCharacterClick = (characterId: string) => {
    if (unavailable.has(characterId)) return;
    if (draft.phase === "ban") {
      const nextSide: Side = draft.bans.A === null ? "A" : "B";
      ban(nextSide, characterId);
    } else if (draft.phase === "pick") {
      const order = draft.pick_order[draft.pick_index];
      pick(order, characterId);
    }
  };

  return (
    <div className="p-8">
      <header className="mb-6">
        <h2 className="text-2xl font-bold">Draft</h2>
        <p className="text-sm text-slate-400">
          Arena <span className="font-semibold">{arena?.name ?? draft.arena_id}</span>{" "}
          {arena?.description && <span className="ml-2 italic">— {arena.description}</span>}
        </p>
        <p className="mt-2 text-sm">
          Phase: <span className="font-semibold uppercase">{draft.phase}</span>
          {draft.phase === "pick" && (
            <>
              {" "}
              · Now picking:{" "}
              <span className="font-semibold">side {draft.pick_order[draft.pick_index]}</span>
            </>
          )}
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        <SideSummary title="Side A" ban={draft.bans.A} picks={draft.picks.A} />
        <SideSummary title="Side B" ban={draft.bans.B} picks={draft.picks.B} />
      </div>

      <h3 className="mt-8 mb-3 text-sm font-semibold uppercase text-slate-400">Pool</h3>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {characters.data.map((c) => (
          <CharacterTile
            key={c.id}
            character={c}
            disabled={unavailable.has(c.id) || draft.phase === "done" || draft.phase === "cancelled"}
            highlight={
              draft.bans.A === c.id || draft.bans.B === c.id
                ? "banned"
                : draft.picks.A.includes(c.id)
                ? "team_a"
                : draft.picks.B.includes(c.id)
                ? "team_b"
                : null
            }
            onClick={() => onCharacterClick(c.id)}
          />
        ))}
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
        Picks:{" "}
        <span className="text-slate-200">{picks.join(", ") || "—"}</span>
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
  highlight: "banned" | "team_a" | "team_b" | null;
  onClick: () => void;
}) {
  const colors = {
    banned: "bg-red-900/40 line-through opacity-60",
    team_a: "bg-blue-900/40 ring-1 ring-blue-500",
    team_b: "bg-amber-900/40 ring-1 ring-amber-500",
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
