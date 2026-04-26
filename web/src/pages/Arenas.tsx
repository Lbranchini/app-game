import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";

export function ArenasPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["arenas"],
    queryFn: api.listArenas,
  });

  if (isLoading) return <p className="p-8">Loading arenas...</p>;
  if (error) return <p className="p-8 text-red-400">Failed: {String(error)}</p>;

  return (
    <div className="p-8">
      <h2 className="mb-6 text-2xl font-bold">Arenas</h2>
      <div className="grid gap-4 md:grid-cols-2">
        {(data ?? []).map((a) => (
          <div key={a.id} className="rounded-xl bg-slate-800 p-5 shadow">
            <h3 className="text-xl font-bold">{a.name}</h3>
            <p className="mt-2 whitespace-pre-line text-sm text-slate-300">{a.description}</p>
            <p className="mt-3 text-xs text-slate-500">
              {a.modifiers.length === 0 ? "No modifiers" : `${a.modifiers.length} modifier(s)`}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
