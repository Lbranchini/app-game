// Mirrors server-side Pydantic models. Keep in sync with server/src/agora/domain/.
// In a future iteration we can codegen this from the OpenAPI schema FastAPI emits.

export type Essence = "vigor" | "spirit" | "mind" | "blood" | "generic";

export type Archetype =
  | "damage_dealer"
  | "healer"
  | "tank"
  | "stunner"
  | "drainer"
  | "trickster"
  | "support"
  | "leader";

export type SkillKind = "instant" | "ongoing" | "control";

export type TargetKind =
  | "single_enemy"
  | "all_enemies"
  | "single_ally"
  | "all_allies"
  | "self";

export type EffectKind =
  | "damage"
  | "heal"
  | "invulnerable"
  | "damage_reduction"
  | "damage_buff"
  | "destructible_shield"
  | "status"
  | "essence_drain"
  | "remove_afflictions";

export interface Effect {
  kind: EffectKind;
  value: number;
  duration: number;
  damage_class: string | null;
  status: string | null;
  piercing: boolean;
  true: boolean;
}

export interface Skill {
  id: string;
  name: string;
  kind: SkillKind;
  cost: Partial<Record<Essence, number>>;
  cooldown: number;
  duration: number;
  target: TargetKind;
  effects: Effect[];
  description?: string;
}

export interface Character {
  id: string;
  name: string;
  mythology: string;
  archetype: Archetype;
  base_hp: number;
  description: string | null;
  skills: Skill[];
}

export interface Arena {
  id: string;
  name: string;
  description: string;
  modifiers: Array<Record<string, unknown>>;
}
