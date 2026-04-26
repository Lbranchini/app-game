import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import type { Character } from "@/types/api";

export function CharactersPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["characters"],
    queryFn: api.listCharacters,
  });

  if (isLoading) return <p className="p-8">Loading characters...</p>;
  if (error) return <p className="p-8 text-red-400">Failed: {String(error)}</p>;

  return (
    <div className="p-8">
      <h2 className="mb-6 text-2xl font-bold">Roster</h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {(data ?? []).map((c) => (
          <CharacterCard key={c.id} character={c} />
        ))}
      </div>
    </div>
  );
}

function CharacterCard({ character }: { character: Character }) {
  return (
    <div className="rounded-xl bg-slate-800 p-5 shadow">
      <div className="flex items-baseline justify-between">
        <h3 className="text-xl font-bold">{character.name}</h3>
        <span className="text-xs uppercase text-slate-400">{character.mythology}</span>
      </div>
      <p className="mt-1 text-sm text-slate-400">
        HP {character.base_hp} • {character.archetype.replace("_", " ")}
      </p>
      <ul className="mt-3 space-y-1 text-sm">
        {character.skills.map((s) => (
          <li key={s.id} className="text-slate-300">
            <span className="font-medium">{s.name}</span>
            <span className="ml-2 text-xs text-slate-500">CD {s.cooldown}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
