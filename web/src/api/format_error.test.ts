import { describe, expect, it } from "vitest";

import { ApiRequestError } from "@/api/client";
import { formatApiError } from "@/api/format_error";
import { translate } from "@/i18n";

describe("formatApiError()", () => {
  const enT = (k: string, fb?: string, vars?: Record<string, string | number>) =>
    translate("en", k, fb, vars);
  const ptT = (k: string, fb?: string, vars?: Record<string, string | number>) =>
    translate("pt-BR", k, fb, vars);

  it("looks up a known server `code` in the active locale", () => {
    const err = new ApiRequestError(404, {
      code: "match.not_found",
      message: "match not found",
      details: null,
    });
    expect(formatApiError(err, enT)).toBe("Match not found.");
    expect(formatApiError(err, ptT)).toBe("Partida não encontrada.");
  });

  it("falls back to the server English `message` for an unknown code", () => {
    const err = new ApiRequestError(500, {
      code: "something.brand_new",
      message: "the server explanation",
      details: null,
    });
    expect(formatApiError(err, ptT)).toBe("the server explanation");
  });

  it("returns the message for a plain Error", () => {
    expect(formatApiError(new Error("boom"), enT)).toBe("boom");
  });

  it("stringifies non-Error values as a last resort", () => {
    expect(formatApiError("oops", enT)).toBe("oops");
    expect(formatApiError(undefined, enT)).toBe("undefined");
  });
});
