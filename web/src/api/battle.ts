// Helpers for assembling actions on the frontend.

import type { Essence, Skill, TargetKind } from "@/types/api";

export interface QueuedAction {
  character_id: string;
  skill_id: string;
  target_ids: string[];
  paid: Partial<Record<Essence, number>>;
}

const ROLLABLE: Essence[] = ["vigor", "spirit", "mind", "blood"];

/**
 * Greedy cost solver: pay specific colors first, then fill generic slots from
 * whichever color the player has most of. Returns null if the player can't
 * afford the skill from `pool`.
 */
export function computePayment(
  cost: Partial<Record<Essence, number>>,
  pool: Partial<Record<Essence, number>>,
): Partial<Record<Essence, number>> | null {
  const remaining: Record<Essence, number> = {
    vigor: pool.vigor ?? 0,
    spirit: pool.spirit ?? 0,
    mind: pool.mind ?? 0,
    blood: pool.blood ?? 0,
    generic: 0,
  };
  const paid: Partial<Record<Essence, number>> = {};

  for (const k of ROLLABLE) {
    const need = cost[k] ?? 0;
    if (need === 0) continue;
    if (remaining[k] < need) return null;
    paid[k] = need;
    remaining[k] -= need;
  }

  let generic = cost.generic ?? 0;
  // Fill from most-abundant color first to leave the rarest essences alone.
  while (generic > 0) {
    const best = ROLLABLE.reduce<Essence | null>(
      (acc, c) => (remaining[c] > 0 && (!acc || remaining[c] > remaining[acc]) ? c : acc),
      null,
    );
    if (!best) return null;
    paid[best] = (paid[best] ?? 0) + 1;
    remaining[best] -= 1;
    generic -= 1;
  }

  return paid;
}

export function subtractPayment(
  pool: Partial<Record<Essence, number>>,
  paid: Partial<Record<Essence, number>>,
): Partial<Record<Essence, number>> {
  const out: Partial<Record<Essence, number>> = { ...pool };
  for (const [k, v] of Object.entries(paid) as [Essence, number][]) {
    out[k] = (out[k] ?? 0) - v;
  }
  return out;
}

export function targetsRequired(skill: Skill): TargetKind {
  return skill.target;
}

export function needsTargetPick(target: TargetKind): boolean {
  return target === "single_enemy" || target === "single_ally";
}
