import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { formatApiError } from "@/api/format_error";
import { useT, type TranslateFn } from "@/i18n";

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

type Outcome = "win" | "loss" | "draw" | "spectator";

async function fetchHistory(): Promise<MatchRecord[]> {
  const response = await fetch("/api/match/history?limit=50");
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

/** Outcome of a match from the viewer's perspective. `spectator` covers
 * the case where the viewer is logged in but wasn't part of the row —
 * the API still surfaces those rows because the history endpoint isn't
 * personal yet. */
function outcomeFor(record: MatchRecord, mySub: string | null): Outcome {
  if (mySub === null) return "spectator";
  const onA = mySub === record.side_a_player_id;
  const onB = mySub === record.side_b_player_id;
  if (!onA && !onB) return "spectator";
  if (record.winner === null) return "draw";
  if ((record.winner === "A" && onA) || (record.winner === "B" && onB)) return "win";
  return "loss";
}

function eloDeltaFor(record: MatchRecord, mySub: string | null): number | null {
  if (mySub === record.side_a_player_id) return record.elo_delta_a;
  if (mySub === record.side_b_player_id) return record.elo_delta_b;
  return record.elo_delta_a; // neutral default for spectator rows
}

export function MatchesPage() {
  const t = useT();
  const me = useQuery({ queryKey: ["me"], queryFn: api.me });
  const history = useQuery({
    queryKey: ["match-history"],
    queryFn: fetchHistory,
    refetchInterval: 5_000,
  });

  const records = history.data ?? [];
  const mySub = me.data?.sub ?? null;

  // Aggregate the viewer's W/L/D + net ELO across the visible window.
  // We only count rows where the viewer actually played; spectator
  // rows skew the win rate and are dropped from the summary.
  const summary = useMemo(() => {
    let wins = 0;
    let losses = 0;
    let draws = 0;
    let netElo = 0;
    let played = 0;
    for (const r of records) {
      const o = outcomeFor(r, mySub);
      if (o === "spectator") continue;
      played += 1;
      if (o === "win") wins += 1;
      else if (o === "loss") losses += 1;
      else draws += 1;
      const delta = eloDeltaFor(r, mySub) ?? 0;
      netElo += delta;
    }
    const winRate = played > 0 ? Math.round((wins / played) * 100) : null;
    return { wins, losses, draws, netElo, played, winRate };
  }, [records, mySub]);

  if (history.isLoading) return <p className="p-8">{t("common.loading")}</p>;
  if (history.error) {
    return (
      <p className="p-8 text-red-400">
        {t("matches.failed", undefined, { error: formatApiError(history.error, t) })}
      </p>
    );
  }

  return (
    <div className="p-8">
      <h2 className="mb-4 text-2xl font-bold">{t("matches.title")}</h2>

      {summary.played > 0 && <SummaryCard summary={summary} t={t} />}

      {records.length === 0 ? (
        <p className="text-slate-400">{t("matches.empty")}</p>
      ) : (
        <table className="w-full overflow-hidden rounded-xl bg-slate-800 text-sm">
          <thead className="bg-slate-900 text-left text-xs uppercase text-slate-400">
            <tr>
              <th className="px-4 py-2">{t("matches.col.when")}</th>
              <th className="px-4 py-2">{t("matches.col.arena")}</th>
              <th className="px-4 py-2">{t("matches.col.sideA")}</th>
              <th className="px-4 py-2">{t("matches.col.sideB")}</th>
              <th className="px-4 py-2">{t("matches.col.outcome", "Outcome")}</th>
              <th className="px-4 py-2">{t("matches.col.turns")}</th>
              <th className="px-4 py-2">{t("matches.col.elo")}</th>
            </tr>
          </thead>
          <tbody>
            {records.map((m) => {
              const outcome = outcomeFor(m, mySub);
              return (
                <tr key={m.id} className="border-t border-slate-700/50">
                  <td className="px-4 py-2 text-slate-400">
                    {new Date(m.started_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-2">{m.arena_id}</td>
                  <td className={`px-4 py-2 ${outcome === "win" || (outcome === "spectator" && m.winner === "A") ? "text-slate-100" : "text-slate-400"}`}>
                    {m.team_a.join(" / ")}
                  </td>
                  <td className={`px-4 py-2 ${outcome === "win" && mySub === m.side_b_player_id ? "text-slate-100" : "text-slate-400"}`}>
                    {m.team_b.join(" / ")}
                  </td>
                  <td className="px-4 py-2">
                    <OutcomeBadge outcome={outcome} winner={m.winner} t={t} />
                  </td>
                  <td className="px-4 py-2 text-slate-400">{m.turns}</td>
                  <td className="px-4 py-2">
                    <EloDelta record={m} mySub={mySub} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

function SummaryCard({
  summary,
  t,
}: {
  summary: {
    wins: number;
    losses: number;
    draws: number;
    netElo: number;
    played: number;
    winRate: number | null;
  };
  t: TranslateFn;
}) {
  const netSign = summary.netElo > 0 ? "+" : "";
  const netColor =
    summary.netElo > 0
      ? "text-emerald-400"
      : summary.netElo < 0
        ? "text-red-400"
        : "text-slate-400";
  return (
    <div className="mb-6 grid grid-cols-2 gap-3 rounded-xl bg-slate-900/60 p-4 ring-1 ring-slate-800 sm:grid-cols-5">
      <Stat label={t("matches.summary.played", "Played")} value={summary.played} />
      <Stat label={t("matches.summary.wins", "Wins")} value={summary.wins} valueClass="text-emerald-400" />
      <Stat label={t("matches.summary.losses", "Losses")} value={summary.losses} valueClass="text-red-400" />
      <Stat label={t("matches.summary.draws", "Draws")} value={summary.draws} valueClass="text-slate-400" />
      <div className="rounded-md bg-slate-950/40 px-3 py-2 ring-1 ring-slate-800/60">
        <div className="text-[10px] uppercase tracking-wider text-slate-500">
          {t("matches.summary.netElo", "Net ELO")}
        </div>
        <div className={`mt-0.5 font-mono text-lg font-bold tabular-nums ${netColor}`}>
          {netSign}
          {summary.netElo}
        </div>
        {summary.winRate !== null && (
          <div className="text-[10px] text-slate-500">
            {t("matches.summary.winRate", "{{rate}}% win rate", { rate: summary.winRate })}
          </div>
        )}
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  valueClass = "text-slate-100",
}: {
  label: string;
  value: number | string;
  valueClass?: string;
}) {
  return (
    <div className="rounded-md bg-slate-950/40 px-3 py-2 ring-1 ring-slate-800/60">
      <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className={`mt-0.5 font-mono text-lg font-bold tabular-nums ${valueClass}`}>{value}</div>
    </div>
  );
}

function OutcomeBadge({
  outcome,
  winner,
  t,
}: {
  outcome: Outcome;
  winner: "A" | "B" | null;
  t: TranslateFn;
}) {
  if (outcome === "spectator") {
    // Viewer didn't play — fall back to the original "Side X" label so
    // the column isn't blank for admin/debug views of the global feed.
    if (winner === "A") return <span className="text-blue-400">A</span>;
    if (winner === "B") return <span className="text-amber-400">B</span>;
    return <span className="text-slate-500">{t("matches.draw")}</span>;
  }
  if (outcome === "win") {
    return (
      <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-xs font-bold text-emerald-200 ring-1 ring-emerald-500/40">
        {t("matches.outcome.win", "Win")}
      </span>
    );
  }
  if (outcome === "loss") {
    return (
      <span className="rounded bg-red-500/20 px-2 py-0.5 text-xs font-bold text-red-200 ring-1 ring-red-500/40">
        {t("matches.outcome.loss", "Loss")}
      </span>
    );
  }
  return (
    <span className="rounded bg-slate-700/40 px-2 py-0.5 text-xs font-bold text-slate-300 ring-1 ring-slate-600/40">
      {t("matches.outcome.draw", "Draw")}
    </span>
  );
}

function EloDelta({ record, mySub }: { record: MatchRecord; mySub: string | null }) {
  const myDelta = eloDeltaFor(record, mySub);
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
