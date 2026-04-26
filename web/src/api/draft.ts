// Typed REST helpers for the draft + match endpoints.

const API = "/api";

export type Side = "A" | "B";

export type DraftPhase =
  | "arena_reveal"
  | "ban"
  | "pick"
  | "confirm"
  | "done"
  | "cancelled";

export interface DraftState {
  draft_id: string;
  arena_id: string;
  side_a_player_id: string;
  side_b_player_id: string;
  phase: DraftPhase;
  bans: Record<Side, string | null>;
  picks: Record<Side, string[]>;
  pick_order: Side[];
  pick_index: number;
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);
  return response.json();
}

export const draftApi = {
  start: (body: { side_a_player_id: string; side_b_player_id: string; arena_id: string }) =>
    call<DraftState>("/draft/start", { method: "POST", body: JSON.stringify(body) }),
  ban: (id: string, side: Side, character_id: string) =>
    call<DraftState>(`/draft/${id}/ban`, {
      method: "POST",
      body: JSON.stringify({ side, character_id }),
    }),
  pick: (id: string, side: Side, character_id: string) =>
    call<DraftState>(`/draft/${id}/pick`, {
      method: "POST",
      body: JSON.stringify({ side, character_id }),
    }),
  finalize: (id: string) =>
    call<{ draft: DraftState; match_id: string }>(`/draft/${id}/finalize`, { method: "POST" }),
  cancel: (id: string) => call<DraftState>(`/draft/${id}/cancel`, { method: "POST" }),
  get: (id: string) => call<DraftState>(`/draft/${id}`),
};
