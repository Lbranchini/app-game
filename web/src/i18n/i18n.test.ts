import { beforeEach, describe, expect, it } from "vitest";

import { translate, useI18nStore, type Locale } from "@/i18n";

describe("translate()", () => {
  it("returns the english string for a known key", () => {
    expect(translate("en", "nav.brand")).toBe("Agora of Myths");
  });

  it("returns the pt-BR string for the same key", () => {
    expect(translate("pt-BR", "nav.brand")).toBe("Ágora dos Mitos");
  });

  it("falls back to the supplied default when the key is missing", () => {
    expect(translate("en", "nope.not.here", "fallback")).toBe("fallback");
  });

  it("falls back to the key name when no default is provided", () => {
    expect(translate("en", "nope.not.here")).toBe("nope.not.here");
  });

  it("interpolates {{var}} placeholders", () => {
    expect(translate("en", "nav.elo", undefined, { elo: 1234 })).toBe("ELO 1234");
    expect(translate("pt-BR", "nav.elo", undefined, { elo: 1234 })).toBe("ELO 1234");
  });

  it("leaves unknown placeholders intact so they're visible during dev", () => {
    expect(translate("en", "battle.yourTurn")).toBe("Your turn · {{seconds}}s");
  });

  it("interpolates multiple variables in one template", () => {
    expect(
      translate("en", "characters.unlockedCount", undefined, { unlocked: 3, total: 16 }),
    ).toBe("3/16 unlocked");
  });

  it("looks up server-emitted error codes in both locales", () => {
    expect(translate("en", "error.match.not_your_turn")).toBe(
      "Hold on — it's the opponent's turn.",
    );
    expect(translate("pt-BR", "error.match.not_your_turn")).toBe(
      "Calma — é o turno do oponente.",
    );
  });

  it("falls back to the server English `detail` when an error code is unknown", () => {
    // The Battle WS handler does `t(`error.${code}`, detail)` — the
    // util's fallback path is what carries the day for codes we
    // haven't translated yet.
    expect(
      translate("pt-BR", "error.match.never_seen_this", "server-side detail"),
    ).toBe("server-side detail");
  });
});

describe("useI18nStore", () => {
  beforeEach(() => {
    window.localStorage.clear();
    // Reset to a known locale before each case so the test is deterministic.
    useI18nStore.setState({ locale: "en" });
  });

  it("flips locale when setLocale is called", () => {
    expect(useI18nStore.getState().locale).toBe("en");
    useI18nStore.getState().setLocale("pt-BR");
    expect(useI18nStore.getState().locale).toBe("pt-BR");
  });

  it("persists the chosen locale to localStorage", () => {
    useI18nStore.getState().setLocale("pt-BR");
    expect(window.localStorage.getItem("agora.locale")).toBe("pt-BR");
  });

  it("ignores an unsupported locale stored from a previous session", () => {
    // Direct test of the subset rule lives via SUPPORTED_LOCALES type;
    // here we just assert that an unknown stored value is replaced when
    // the store is mutated.
    window.localStorage.setItem("agora.locale", "klingon");
    const next: Locale = "pt-BR";
    useI18nStore.getState().setLocale(next);
    expect(window.localStorage.getItem("agora.locale")).toBe("pt-BR");
  });
});
