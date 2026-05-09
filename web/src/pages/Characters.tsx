import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { api, type UnlockRulePayload } from "@/api/client";
import { formatApiError } from "@/api/format_error";
import { useT, type TranslateFn } from "@/i18n";
import type { Character } from "@/types/api";

export function CharactersPage() {
  const t = useT();
  const characters = useQuery({ queryKey: ["characters"], queryFn: api.listCharacters });
  const me = useQuery({ queryKey: ["me"], queryFn: api.me, refetchInterval: 30_000 });
  const rules = useQuery({ queryKey: ["unlock-rules"], queryFn: api.listUnlockRules });

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

  const unlockedChars = playerKnown ? all.filter((c) => unlocked.has(c.id)) : all;
  const lockedChars = playerKnown ? all.filter((c) => !unlocked.has(c.id)) : [];

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

      <h3 className="mb-3 text-sm font-semibold uppercase text-slate-400">{t("characters.unlocked")}</h3>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {unlockedChars.map((c) => (
          <CharacterCard key={c.id} character={c} t={t} />
        ))}
      </div>

      {lockedChars.length > 0 && (
        <>
          <h3 className="mt-10 mb-3 text-sm font-semibold uppercase text-slate-400">{t("characters.locked")}</h3>
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
    </div>
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
          archetype: character.archetype.replace("_", " "),
        })}
      </p>
      <ul className="mt-3 space-y-1 text-sm">
        {character.skills.map((s) => (
          <li key={s.id} className="text-slate-300">
            <span className="font-medium">{t(`skill.${s.id}.name`, s.name)}</span>
            <span className="ml-2 text-xs text-slate-500">
              {t("battle.cooldown", undefined, { turns: s.cooldown })}
            </span>
          </li>
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
          archetype: character.archetype.replace("_", " "),
        })}
      </p>
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
      <ul className="mt-4 space-y-1 border-t border-slate-800 pt-3 text-xs">
        {character.skills.map((s) => (
          <li key={s.id} className="text-slate-500">
            <span className="font-medium text-slate-400">{t(`skill.${s.id}.name`, s.name)}</span>
            <span className="ml-2 text-slate-600">
              {t("battle.cooldown", undefined, { turns: s.cooldown })}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
