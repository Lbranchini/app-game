import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api, type UnlockRulePayload } from "@/api/client";
import { formatApiError } from "@/api/format_error";
import { useT, type TranslateFn } from "@/i18n";
import { buildSkillDescription } from "@/lib/skill_description";
import type { Character, Essence, Skill } from "@/types/api";

const ESSENCE_DOT: Record<Essence, string> = {
  vigor: "bg-red-500",
  spirit: "bg-amber-400",
  mind: "bg-sky-400",
  blood: "bg-fuchsia-500",
  generic: "bg-slate-400",
};
const ESSENCE_ORDER: Essence[] = ["vigor", "spirit", "mind", "blood"];

export function CharactersPage() {
  const t = useT();
  const characters = useQuery({ queryKey: ["characters"], queryFn: api.listCharacters });
  const me = useQuery({ queryKey: ["me"], queryFn: api.me, refetchInterval: 30_000 });
  const rules = useQuery({ queryKey: ["unlock-rules"], queryFn: api.listUnlockRules });

  // URL-synced filter state so a refresh (or a shared link) keeps the
  // viewer's filters. Empty strings drop the key from the URL — keeps
  // the bar above the address line legible while everything's selected.
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get("q") ?? "";
  const mythologyFilter = searchParams.get("mythology") ?? "";
  const archetypeFilter = searchParams.get("archetype") ?? "";

  const setFilter = (key: "q" | "mythology" | "archetype", value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next, { replace: true });
  };

  const ruleByCharacter = useMemo(() => {
    const map = new Map<string, UnlockRulePayload>();
    (rules.data ?? []).forEach((r) => map.set(r.character_id, r));
    return map;
  }, [rules.data]);

  if (characters.isLoading) return <p className="p-8">{t("characters.loading")}</p>;
  if (characters.error) {
    return (
      <p className="p-8 text-red-400">
        {t("characters.failed", undefined, { error: formatApiError(characters.error, t) })}
      </p>
    );
  }

  const all = characters.data ?? [];
  const unlocked = new Set(me.data?.player?.unlocked_characters ?? []);
  const progress = me.data?.player?.progress ?? {};

  // Hide the unlock metadata until /auth/me has hydrated. Without a player row
  // (e.g. /auth/dev-token) we just show everything as available — no roster
  // exists to filter against.
  const playerKnown = Boolean(me.data?.player);

  // Aggregate the filter chips off the actual roster so adding a new
  // mythology/archetype in YAML lights up its chip automatically.
  const mythologies = [...new Set(all.map((c) => c.mythology))].sort();
  const archetypes = [...new Set(all.map((c) => c.archetype))].sort();

  const matchesQuery = (c: Character) => {
    if (!query) return true;
    const q = query.toLowerCase();
    return (
      c.name.toLowerCase().includes(q) ||
      c.mythology.toLowerCase().includes(q) ||
      c.archetype.toLowerCase().includes(q)
    );
  };
  const passes = (c: Character) =>
    matchesQuery(c) &&
    (!mythologyFilter || c.mythology === mythologyFilter) &&
    (!archetypeFilter || c.archetype === archetypeFilter);

  const filtered = all.filter(passes);
  const unlockedChars = playerKnown ? filtered.filter((c) => unlocked.has(c.id)) : filtered;
  const lockedChars = playerKnown ? filtered.filter((c) => !unlocked.has(c.id)) : [];
  const noResults = filtered.length === 0;
  const filtersActive = Boolean(query || mythologyFilter || archetypeFilter);

  return (
    <div className="p-8">
      <header className="mb-6 flex items-baseline justify-between">
        <h2 className="text-2xl font-bold">{t("characters.title")}</h2>
        {playerKnown && (
          <p className="text-sm text-slate-400">
            {t("characters.unlockedCount", undefined, {
              unlocked: unlockedChars.length,
              total: all.length,
            })}
          </p>
        )}
      </header>

      <FilterBar
        t={t}
        query={query}
        onQueryChange={(v) => setFilter("q", v)}
        mythologies={mythologies}
        mythologyFilter={mythologyFilter}
        onMythologyChange={(v) => setFilter("mythology", v)}
        archetypes={archetypes}
        archetypeFilter={archetypeFilter}
        onArchetypeChange={(v) => setFilter("archetype", v)}
        clearAll={() => setSearchParams({}, { replace: true })}
        filtersActive={filtersActive}
      />

      {noResults ? (
        <p className="mt-8 text-sm italic text-slate-500">
          {t("characters.noResults", "No characters match those filters.")}
        </p>
      ) : (
        <>
          {(unlockedChars.length > 0 || !playerKnown) && (
            <>
              <h3 className="mb-3 text-sm font-semibold uppercase text-slate-400">
                {t("characters.unlocked")}
              </h3>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {unlockedChars.map((c) => (
                  <CharacterCard key={c.id} character={c} t={t} />
                ))}
              </div>
            </>
          )}

          {lockedChars.length > 0 && (
            <>
              <h3 className="mt-10 mb-3 text-sm font-semibold uppercase text-slate-400">
                {t("characters.locked")}
              </h3>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {lockedChars.map((c) => (
                  <LockedCharacterCard
                    key={c.id}
                    character={c}
                    rule={ruleByCharacter.get(c.id) ?? null}
                    progress={progress}
                    t={t}
                  />
                ))}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}

function FilterBar({
  t,
  query,
  onQueryChange,
  mythologies,
  mythologyFilter,
  onMythologyChange,
  archetypes,
  archetypeFilter,
  onArchetypeChange,
  clearAll,
  filtersActive,
}: {
  t: TranslateFn;
  query: string;
  onQueryChange: (value: string) => void;
  mythologies: string[];
  mythologyFilter: string;
  onMythologyChange: (value: string) => void;
  archetypes: string[];
  archetypeFilter: string;
  onArchetypeChange: (value: string) => void;
  clearAll: () => void;
  filtersActive: boolean;
}) {
  return (
    <div className="mb-6 space-y-3 rounded-xl bg-slate-900/50 p-4 ring-1 ring-slate-800">
      <div className="flex items-center gap-3">
        <input
          type="search"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder={t("characters.searchPlaceholder", "Search by name, mythology, archetype")}
          className="flex-1 rounded-md bg-slate-950 px-3 py-1.5 text-sm text-slate-100 ring-1 ring-slate-800 placeholder:text-slate-600 focus:outline-none focus:ring-emerald-500/60"
        />
        {filtersActive && (
          <button
            type="button"
            onClick={clearAll}
            className="rounded-md bg-slate-800 px-3 py-1.5 text-xs text-slate-300 ring-1 ring-slate-700 hover:bg-slate-700"
          >
            {t("characters.filter.clearAll", "Clear filters")}
          </button>
        )}
      </div>

      <FilterChips
        legend={t("characters.filter.mythology", "Mythology")}
        all={mythologies}
        selected={mythologyFilter}
        onSelect={onMythologyChange}
        labelFor={(value) => t(`characters.mythology.${value.toLowerCase()}`, value)}
      />
      <FilterChips
        legend={t("characters.filter.archetype", "Archetype")}
        all={archetypes}
        selected={archetypeFilter}
        onSelect={onArchetypeChange}
        labelFor={(value) =>
          t(`characters.archetype.${value}`, value.replace(/_/g, " "))
        }
      />
    </div>
  );
}

function FilterChips({
  legend,
  all,
  selected,
  onSelect,
  labelFor,
}: {
  legend: string;
  all: string[];
  selected: string;
  onSelect: (value: string) => void;
  labelFor: (value: string) => string;
}) {
  return (
    <div className="flex flex-wrap items-center gap-1.5 text-xs">
      <span className="mr-1 text-[10px] uppercase tracking-wider text-slate-500">{legend}</span>
      {all.map((value) => {
        const active = selected === value;
        return (
          <button
            key={value}
            type="button"
            onClick={() => onSelect(active ? "" : value)}
            aria-pressed={active}
            className={[
              "rounded-full px-2.5 py-0.5 capitalize transition",
              active
                ? "bg-emerald-500/20 text-emerald-200 ring-1 ring-emerald-500/60"
                : "bg-slate-800 text-slate-400 ring-1 ring-slate-700 hover:bg-slate-700",
            ].join(" ")}
          >
            {labelFor(value)}
          </button>
        );
      })}
    </div>
  );
}

function CostPips({ cost }: { cost: Partial<Record<Essence, number>> }) {
  const pips: string[] = [];
  for (const k of ESSENCE_ORDER) {
    const n = cost[k] ?? 0;
    for (let i = 0; i < n; i++) pips.push(ESSENCE_DOT[k]);
  }
  const generic = cost.generic ?? 0;
  for (let i = 0; i < generic; i++) pips.push(ESSENCE_DOT.generic);
  if (pips.length === 0) return null;
  return (
    <span className="inline-flex items-center gap-0.5">
      {pips.map((color, i) => (
        <span key={i} className={`inline-block h-1.5 w-1.5 rounded-full ${color}`} />
      ))}
    </span>
  );
}

function SkillLine({ skill, t, muted = false }: { skill: Skill; t: TranslateFn; muted?: boolean }) {
  // YAML description wins; i18n override sits in front of it; engine
  // fallback synthesises a sentence from the effect list when neither
  // is present (covers the 10 characters whose YAML hasn't been
  // annotated yet).
  const yamlDesc = skill.description?.trim() || buildSkillDescription(skill);
  const desc = t(`skill.${skill.id}.description`, yamlDesc);
  return (
    <li className={muted ? "text-slate-500" : "text-slate-300"}>
      <div className="flex items-baseline justify-between gap-2">
        <span className={muted ? "font-medium text-slate-400" : "font-semibold text-slate-100"}>
          {t(`skill.${skill.id}.name`, skill.name)}
        </span>
        <span className="inline-flex items-center gap-2 text-xs text-slate-500 shrink-0">
          <CostPips cost={skill.cost} />
          {skill.cooldown > 0 && (
            <span>{t("battle.cooldown", undefined, { turns: skill.cooldown })}</span>
          )}
        </span>
      </div>
      <p className="mt-0.5 text-xs leading-relaxed text-slate-400">{desc}</p>
    </li>
  );
}

function CharacterTagline({ character, t }: { character: Character; t: TranslateFn }) {
  // YAML carries an English tagline; the i18n key lets a translator
  // override per locale. Empty taglines render nothing.
  const yamlDesc = character.description?.trim() ?? "";
  const tagline = t(`character.${character.id}.description`, yamlDesc);
  if (!tagline) return null;
  return (
    <p className="mt-2 text-sm italic leading-relaxed text-slate-400">{tagline}</p>
  );
}

function CharacterCard({ character, t }: { character: Character; t: TranslateFn }) {
  return (
    <div className="rounded-xl bg-slate-800 p-5 shadow">
      <div className="flex items-baseline justify-between">
        <h3 className="text-xl font-bold">{character.name}</h3>
        <span className="text-xs uppercase text-slate-400">{character.mythology}</span>
      </div>
      <p className="mt-1 text-sm text-slate-400">
        {t("characters.openSubtitle", undefined, {
          hp: character.base_hp,
          archetype: t(`characters.archetype.${character.archetype}`, character.archetype.replace(/_/g, " ")),
        })}
      </p>
      <CharacterTagline character={character} t={t} />
      <ul className="mt-4 space-y-3 border-t border-slate-700 pt-3 text-sm">
        {character.skills.map((s) => (
          <SkillLine key={s.id} skill={s} t={t} />
        ))}
      </ul>
    </div>
  );
}

function LockedCharacterCard({
  character,
  rule,
  progress,
  t,
}: {
  character: Character;
  rule: UnlockRulePayload | null;
  progress: Record<string, number>;
  t: TranslateFn;
}) {
  const current =
    rule?.progress_key !== null && rule?.progress_key !== undefined
      ? progress[rule.progress_key] ?? 0
      : null;
  const target = rule?.target ?? null;
  const ratio =
    current !== null && target !== null && target > 0 ? Math.min(1, current / target) : null;

  return (
    <div className="rounded-xl bg-slate-900/60 p-5 shadow ring-1 ring-slate-800">
      <div className="flex items-baseline justify-between">
        <h3 className="text-xl font-semibold text-slate-300">{character.name}</h3>
        <span className="text-xs uppercase text-slate-500">{character.mythology}</span>
      </div>
      <p className="mt-1 text-sm text-slate-500">
        {t("characters.lockedSubtitle", undefined, {
          hp: character.base_hp,
          archetype: t(`characters.archetype.${character.archetype}`, character.archetype.replace(/_/g, " ")),
        })}
      </p>
      <CharacterTagline character={character} t={t} />
      {rule ? (
        <>
          <p className="mt-3 text-sm text-slate-300">{rule.description}</p>
          {current !== null && target !== null && (
            <>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full bg-emerald-500 transition-all"
                  style={{ width: `${(ratio ?? 0) * 100}%` }}
                />
              </div>
              <p className="mt-1 text-xs text-slate-400">
                {current} / {target}
              </p>
            </>
          )}
        </>
      ) : (
        <p className="mt-3 text-xs italic text-slate-500">{t("characters.noUnlockRule")}</p>
      )}
      <ul className="mt-4 space-y-2 border-t border-slate-800 pt-3 text-xs">
        {character.skills.map((s) => (
          <SkillLine key={s.id} skill={s} t={t} muted />
        ))}
      </ul>
    </div>
  );
}
