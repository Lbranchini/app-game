import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";

interface MatchRecord {
  id: string;
  arena_id: string;
  side_a_player_id: string;
  side_b_player_id: string;
  team_a: string[];
  team_b: string[];
  winner: "A" | "B" | null;
  turns: number;
  started_at: string;
  ended_at: string | null;
  elo_delta_a: number | null;
  elo_delta_b: number | null;
}

async function fetchHistory(): Promise<MatchRecord[]> {
  const response = await fetch("/api/match/history?limit=50");
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export function MatchesPage() {
  const me = useQuery({ queryKey: ["me"], queryFn: api.me });
  const history = useQuery({
    queryKey: ["match-history"],
    queryFn: fetchHistory,
    refetchInterval: 5_000,
  });

  if (history.isLoading) return <p className="p-8">Loading…</p>;
  if (history.error) return <p className="p-8 text-red-400">Failed: {String(history.error)}</p>;

  const records = history.data ?? [];
  const mySub = me.data?.sub ?? null;

  return (
    <div className="p-8">
      <h2 className="mb-4 text-2xl font-bold">Recent matches</h2>
      {records.length === 0 ? (
        <p className="text-slate-400">No matches yet — finish one and it'll show up here.</p>
      ) : (
        <table className="w-full overflow-hidden rounded-xl bg-slate-800 text-sm">
          <thead className="bg-slate-900 text-left text-xs uppercase text-slate-400">
            <tr>
              <th className="px-4 py-2">When</th>
              <th className="px-4 py-2">Arena</th>
              <th className="px-4 py-2">Side A</th>
              <th className="px-4 py-2">Side B</th>
              <th className="px-4 py-2">Winner</th>
              <th className="px-4 py-2">Turns</th>
              <th className="px-4 py-2">ELO Δ</th>
            </tr>
          </thead>
          <tbody>
            {records.map((m) => (
              <tr key={m.id} className="border-t border-slate-700/50">
                <td className="px-4 py-2 text-slate-400">
                  {new Date(m.started_at).toLocaleString()}
                </td>
                <td className="px-4 py-2">{m.arena_id}</td>
                <td className="px-4 py-2 text-slate-200">{m.team_a.join(" / ")}</td>
                <td className="px-4 py-2 text-slate-200">{m.team_b.join(" / ")}</td>
                <td className="px-4 py-2">
                  {m.winner === "A" && <span className="text-blue-400">A</span>}
                  {m.winner === "B" && <span className="text-amber-400">B</span>}
                  {m.winner === null && <span className="text-slate-500">draw</span>}
                </td>
                <td className="px-4 py-2 text-slate-400">{m.turns}</td>
                <td className="px-4 py-2">
                  <EloDelta record={m} mySub={mySub} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function EloDelta({ record, mySub }: { record: MatchRecord; mySub: string | null }) {
  // Show the delta from the viewer's perspective when they participated;
  // otherwise show side A's delta as a neutral default.
  const myDelta =
    mySub === record.side_a_player_id
      ? record.elo_delta_a
      : mySub === record.side_b_player_id
      ? record.elo_delta_b
      : record.elo_delta_a;

  if (myDelta === null || myDelta === undefined) {
    return <span className="text-slate-600">—</span>;
  }
  if (myDelta > 0) {
    return <span className="text-emerald-400">+{myDelta}</span>;
  }
  if (myDelta < 0) {
    return <span className="text-red-400">{myDelta}</span>;
  }
  return <span className="text-slate-400">0</span>;
}
