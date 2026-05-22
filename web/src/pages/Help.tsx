import { useT, type TranslateFn } from "@/i18n";

const STATUS_IDS = [
  "stun",
  "silence",
  "disarm",
  "stealth",
  "reflective",
  "invulnerable",
  "damage_reduction",
  "damage_buff",
  "poison",
  "bleed",
  "regen",
  "marked",
  "vulnerable",
  "drained",
  "shield",
] as const;

const SECTIONS = [
  { id: "match", labelKey: "help.toc.match" },
  { id: "essences", labelKey: "help.toc.essences" },
  { id: "skills", labelKey: "help.toc.skills" },
  { id: "statuses", labelKey: "help.toc.statuses" },
] as const;

export function HelpPage() {
  const t = useT();
  return (
    <div className="mx-auto max-w-3xl p-8">
      <header className="mb-6">
        <h2 className="text-2xl font-bold">{t("help.title")}</h2>
        <p className="mt-1 text-sm text-slate-400">{t("help.tagline")}</p>
      </header>

      <nav
        aria-label={t("help.toc.title")}
        className="mb-8 flex flex-wrap gap-2 rounded-lg bg-slate-900/60 p-3 ring-1 ring-slate-800"
      >
        {SECTIONS.map((s) => (
          <a
            key={s.id}
            href={`#${s.id}`}
            className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300 ring-1 ring-slate-700 hover:bg-slate-700"
          >
            {t(s.labelKey)}
          </a>
        ))}
      </nav>

      <Section id="match" title={t("help.match.title")}>
        <Paragraph>{t("help.match.format")}</Paragraph>
        <Paragraph>{t("help.match.flow")}</Paragraph>
        <Paragraph>{t("help.match.timer")}</Paragraph>
        <Paragraph>{t("help.match.win")}</Paragraph>
      </Section>

      <Section id="essences" title={t("help.essences.title")}>
        <Paragraph>{t("help.essences.intro")}</Paragraph>
        <ul className="mt-2 space-y-1 text-sm">
          <EssenceLine color="bg-red-500" name={t("help.essences.vigor")} desc={t("help.essences.vigor.desc")} />
          <EssenceLine color="bg-amber-400" name={t("help.essences.spirit")} desc={t("help.essences.spirit.desc")} />
          <EssenceLine color="bg-sky-400" name={t("help.essences.mind")} desc={t("help.essences.mind.desc")} />
          <EssenceLine color="bg-fuchsia-500" name={t("help.essences.blood")} desc={t("help.essences.blood.desc")} />
          <EssenceLine color="bg-slate-400" name={t("help.essences.generic")} desc={t("help.essences.generic.desc")} />
        </ul>
        <Paragraph>{t("help.essences.generation")}</Paragraph>
      </Section>

      <Section id="skills" title={t("help.skills.title")}>
        <Paragraph>{t("help.skills.intro")}</Paragraph>
        <Paragraph>{t("help.skills.cost")}</Paragraph>
        <Paragraph>{t("help.skills.cooldown")}</Paragraph>
        <Paragraph>{t("help.skills.targets")}</Paragraph>
        <Paragraph>{t("help.skills.queue")}</Paragraph>
      </Section>

      <Section id="statuses" title={t("help.statuses.title")}>
        <Paragraph>{t("help.statuses.intro")}</Paragraph>
        <ul className="mt-3 grid gap-2 sm:grid-cols-2">
          {STATUS_IDS.map((id) => (
            <StatusEntry key={id} id={id} t={t} />
          ))}
        </ul>
      </Section>
    </div>
  );
}

function Section({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="mb-10 scroll-mt-20">
      <h3 className="mb-3 text-lg font-bold uppercase tracking-wider text-slate-300">{title}</h3>
      <div className="space-y-2 rounded-xl bg-slate-900/40 p-5 ring-1 ring-slate-800">
        {children}
      </div>
    </section>
  );
}

function Paragraph({ children }: { children: React.ReactNode }) {
  return <p className="text-sm leading-relaxed text-slate-300">{children}</p>;
}

function EssenceLine({ color, name, desc }: { color: string; name: string; desc: string }) {
  return (
    <li className="flex items-baseline gap-2 text-sm text-slate-300">
      <span className={`inline-block h-2 w-2 shrink-0 rounded-full ${color}`} />
      <span>
        <span className="font-semibold text-slate-100">{name}</span>
        <span className="ml-1 text-slate-400">— {desc}</span>
      </span>
    </li>
  );
}

function StatusEntry({ id, t }: { id: string; t: TranslateFn }) {
  return (
    <li className="rounded-md bg-slate-950/40 px-3 py-2 ring-1 ring-slate-800/60">
      <div className="text-xs font-bold uppercase tracking-wider text-slate-100">
        {t(`status.${id}.label`, id)}
      </div>
      <div className="mt-0.5 text-xs text-slate-400">
        {t(`status.${id}.description`, t("status.fallback.description"))}
      </div>
    </li>
  );
}
