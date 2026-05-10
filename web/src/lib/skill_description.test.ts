import { describe, expect, it } from "vitest";

import { buildSkillDescription, targetLabel } from "@/lib/skill_description";
import type { Effect, Skill } from "@/types/api";

function makeEffect(overrides: Partial<Effect>): Effect {
  return {
    kind: "damage",
    value: 0,
    duration: 0,
    damage_class: null,
    status: null,
    piercing: false,
    true: false,
    ...overrides,
  };
}

function makeSkill(overrides: Partial<Skill>): Skill {
  return {
    id: "test",
    name: "Test",
    kind: "instant",
    cost: {},
    cooldown: 0,
    duration: 0,
    target: "single_enemy",
    description: "",
    effects: [],
    ...overrides,
  };
}

describe("targetLabel()", () => {
  it("maps the documented target kinds", () => {
    expect(targetLabel("single_enemy")).toBe("one enemy");
    expect(targetLabel("all_enemies")).toBe("all enemies");
    expect(targetLabel("single_ally")).toBe("one ally");
    expect(targetLabel("all_allies")).toBe("all allies");
    expect(targetLabel("self")).toBe("this character");
  });

  it("falls back for unknown kinds", () => {
    expect(targetLabel("unknown_thing")).toBe("the target");
  });
});

describe("buildSkillDescription()", () => {
  it("renders damage with target + class", () => {
    const skill = makeSkill({
      effects: [makeEffect({ kind: "damage", value: 20, damage_class: "physical" })],
    });
    expect(buildSkillDescription(skill)).toBe(
      "Deals 20 physical damage to one enemy.",
    );
  });

  it("notes piercing on damage effects", () => {
    const skill = makeSkill({
      effects: [
        makeEffect({ kind: "damage", value: 40, damage_class: "physical", piercing: true }),
      ],
    });
    expect(buildSkillDescription(skill)).toBe(
      "Deals 40 physical damage to one enemy. Ignores damage reduction.",
    );
  });

  it("describes status effects with duration", () => {
    const skill = makeSkill({
      effects: [makeEffect({ kind: "status", status: "poison", duration: 2, value: 10 })],
    });
    expect(buildSkillDescription(skill)).toBe(
      "Inflicts poison on one enemy for 2 turns.",
    );
  });

  it("chains multiple effects into one sentence run", () => {
    const skill = makeSkill({
      cooldown: 2,
      effects: [
        makeEffect({ kind: "damage", value: 35, damage_class: "physical" }),
        makeEffect({ kind: "status", status: "bleed", duration: 2, value: 10 }),
      ],
    });
    expect(buildSkillDescription(skill)).toContain("Deals 35 physical damage");
    expect(buildSkillDescription(skill)).toContain("Inflicts bleed");
    expect(buildSkillDescription(skill)).toContain("2-turn cooldown");
  });

  it("falls back when no effects matched", () => {
    expect(buildSkillDescription(makeSkill({}))).toBe("No description available.");
  });

  it("describes heals with the localized target", () => {
    const skill = makeSkill({
      target: "single_ally",
      effects: [makeEffect({ kind: "heal", value: 25 })],
    });
    expect(buildSkillDescription(skill)).toBe("Restores 25 HP to one ally.");
  });
});
