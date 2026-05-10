/**
 * Skill description synthesizer.
 *
 * If a skill's YAML description is empty we still want to show *something*
 * useful in tooltips and on the Characters page. This module reads the
 * structured `effects` list and produces an English fallback sentence
 * per effect.
 *
 * Lives outside Battle.tsx so the Characters page can reuse it.
 */

import type { Skill } from "@/types/api";

export function targetLabel(target: string): string {
  switch (target) {
    case "single_enemy":
      return "one enemy";
    case "all_enemies":
      return "all enemies";
    case "single_ally":
      return "one ally";
    case "all_allies":
      return "all allies";
    case "self":
      return "this character";
    default:
      return "the target";
  }
}

export function buildSkillDescription(skill: Skill): string {
  const parts: string[] = [];
  for (const ef of skill.effects) {
    const tgt = targetLabel(skill.target);
    switch (ef.kind) {
      case "damage": {
        const cls = ef.damage_class ? `${ef.damage_class} ` : "";
        let s = `Deals ${ef.value} ${cls}damage to ${tgt}.`;
        if (ef.piercing) s += " Ignores damage reduction.";
        parts.push(s);
        break;
      }
      case "heal":
        parts.push(`Restores ${ef.value} HP to ${tgt}.`);
        break;
      case "status":
        parts.push(
          `Inflicts ${ef.status ?? "a status effect"} on ${tgt}` +
            (ef.duration > 0
              ? ` for ${ef.duration} turn${ef.duration !== 1 ? "s" : ""}`
              : "") +
            ".",
        );
        break;
      case "destructible_shield":
        parts.push(`Grants ${tgt} ${ef.value} points of destructible defense.`);
        break;
      case "invulnerable":
        parts.push(
          `Makes ${tgt} invulnerable for ${ef.duration} turn${
            ef.duration !== 1 ? "s" : ""
          }.`,
        );
        break;
      case "damage_reduction":
        parts.push(
          `Reduces damage taken by ${tgt} by ${ef.value}` +
            (ef.duration > 0
              ? ` for ${ef.duration} turn${ef.duration !== 1 ? "s" : ""}`
              : "") +
            ".",
        );
        break;
      case "damage_buff":
        parts.push(
          `Increases damage dealt by ${tgt} by ${ef.value}` +
            (ef.duration > 0
              ? ` for ${ef.duration} turn${ef.duration !== 1 ? "s" : ""}`
              : "") +
            ".",
        );
        break;
      case "essence_drain":
        parts.push(`Drains ${ef.value} essence from ${tgt}.`);
        break;
      case "remove_afflictions":
        parts.push(`Removes all afflictions from ${tgt}.`);
        break;
    }
  }
  if (skill.cooldown > 0)
    parts.push(`Enters a ${skill.cooldown}-turn cooldown after use.`);
  return parts.join(" ") || "No description available.";
}
