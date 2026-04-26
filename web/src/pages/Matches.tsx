import { useQuery } from "@tanstack/react-query";

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
}

async function fetchHistory(): Promise<MatchRecord[]> {
  const response = await fetch("/api/match/history?limit=50");
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export function MatchesPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["match-history"],
    queryFn: fetchHistory,
    refetchInterval: 5_000,
  });

  if (isLoading) return <p className="p-8">Loading…</p>;
  if (error) return <p className="p-8 text-red-400">Failed: {String(error)}</p>;

  const records = data ?? [];

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
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
