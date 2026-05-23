import { useQuery } from "@tanstack/react-query";

import { api, type PlayerProfile } from "@/api/client";
import { useT, type TranslateFn } from "@/i18n";

export function ProfilePage() {
  const t = useT();
  const me = useQuery({ queryKey: ["me"], queryFn: api.me, refetchInterval: 30_000 });

  if (me.isLoading) return <p className="p-8">{t("common.loading")}</p>;
  const player = me.data?.player;
  if (!player) {
    return (
      <div className="p-8 text-sm text-slate-400">{t("profile.noPlayer")}</div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl p-8">
      <Header player={player} displayName={me.data?.player?.name ?? me.data?.sub ?? null} t={t} />

      <CareerStats player={player} t={t} />
      <CombatStats player={player} t={t} />
      <StatusMastery player={player} t={t} />
    </div>
  );
}

function Header({
  player,
  displayName,
  t,
}: {
  player: PlayerProfile;
  displayName: string | null;
  t: TranslateFn;
}) {
  return (
    <header className="mb-6 flex items-baseline justify-between rounded-xl bg-slate-900/60 px-5 py-4 ring-1 ring-slate-800">
      <div>
        <h2 className="text-2xl font-bold">{displayName ?? t("common.you")}</h2>
        <p className="text-xs uppercase tracking-wider text-slate-500">
          {player.provider_subject}
        </p>
      </div>
      <div className="text-right">
        <div className="text-[10px] uppercase tracking-wider text-slate-500">ELO</div>
        <div className="font-mono text-2xl font-bold tabular-nums text-emerald-400">
          {player.elo}
        </div>
        <div className="mt-1 text-[10px] text-slate-500">
          {t("profile.unlocked", undefined, { count: player.unlocked_characters.length })}
        </div>
      </div>
    </header>
  );
}

function CareerStats({ player, t }: { player: PlayerProfile; t: TranslateFn }) {
  const p = player.progress;
  const played = p.matches_played ?? 0;
  const wins = p.wins ?? 0;
  const losses = p.losses ?? 0;
  const draws = p.draws ?? 0;
  const winRate = played > 0 ? Math.round((wins / played) * 100) : null;

  return (
    <Section title={t("profile.career.title")}>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label={t("profile.career.played")} value={played} />
        <Stat label={t("profile.career.wins")} value={wins} valueClass="text-emerald-400" />
        <Stat label={t("profile.career.losses")} value={losses} valueClass="text-red-400" />
        <Stat label={t("profile.career.draws")} value={draws} valueClass="text-slate-400" />
      </div>
      {winRate !== null && (
        <p className="mt-3 text-xs text-slate-500">
          {t("profile.career.winRate", undefined, { rate: winRate })}
        </p>
      )}
    </Section>
  );
}

function CombatStats({ player, t }: { player: PlayerProfile; t: TranslateFn }) {
  const p = player.progress;
  const dealt = p.total_damage_dealt ?? 0;
  const taken = p.total_damage_taken ?? 0;
  const healed = p.total_healing_done ?? 0;
  // Nothing accumulated yet — skip the section so a brand-new player
  // doesn't see a row of zeros.
  if (dealt + taken + healed === 0) return null;
  return (
    <Section title={t("profile.combat.title")}>
      <div className="grid grid-cols-3 gap-3">
        <Stat label={t("profile.combat.dealt")} value={dealt} valueClass="text-red-300" />
        <Stat label={t("profile.combat.taken")} value={taken} valueClass="text-amber-300" />
        <Stat label={t("profile.combat.healed")} value={healed} valueClass="text-emerald-300" />
      </div>
    </Section>
  );
}

function StatusMastery({ player, t }: { player: PlayerProfile; t: TranslateFn }) {
  // Pull every `status_applied.<name>` key, biggest first. If the player
  // hasn't landed any statuses on opponents yet, skip the section.
  const entries: Array<[string, number]> = [];
  for (const [key, value] of Object.entries(player.progress)) {
    if (key.startsWith("status_applied.") && value > 0) {
      entries.push([key.slice("status_applied.".length), value]);
    }
  }
  if (entries.length === 0) return null;
  entries.sort((a, b) => b[1] - a[1]);

  return (
    <Section title={t("profile.mastery.title")}>
      <p className="mb-3 text-xs text-slate-500">{t("profile.mastery.tagline")}</p>
      <ul className="grid gap-2 sm:grid-cols-2">
        {entries.map(([name, count]) => (
          <li
            key={name}
            className="flex items-center justify-between rounded-md bg-slate-950/40 px-3 py-2 ring-1 ring-slate-800/60"
          >
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-100">
              {t(`status.${name}.label`, name)}
            </span>
            <span className="font-mono text-sm font-bold tabular-nums text-slate-300">
              {count}
            </span>
          </li>
        ))}
      </ul>
    </Section>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-6 rounded-xl bg-slate-900/40 p-5 ring-1 ring-slate-800">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
        {title}
      </h3>
      {children}
    </section>
  );
}

function Stat({
  label,
  value,
  valueClass = "text-slate-100",
}: {
  label: string;
  value: number;
  valueClass?: string;
}) {
  return (
    <div className="rounded-md bg-slate-950/40 px-3 py-2 ring-1 ring-slate-800/60">
      <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className={`mt-0.5 font-mono text-lg font-bold tabular-nums ${valueClass}`}>
        {value.toLocaleString()}
      </div>
    </div>
  );
}
