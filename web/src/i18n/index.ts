/**
 * Tiny i18n utility — no external dep, ~50 lines.
 *
 * Locale detection order: explicit `localStorage["agora.locale"]`
 * > `navigator.language` (PT prefix → pt-BR) > `en`. Switching locales
 * via `setLocale` updates the Zustand store so every consumer of
 * `useT()` re-renders, no full reload needed.
 *
 * String interpolation: `{{var}}` placeholders are replaced from the
 * `vars` argument. Missing keys fall back to `fallback` if provided
 * (typed dev-time English), otherwise the key itself.
 */

import { useCallback } from "react";
import { create } from "zustand";

import { en } from "@/i18n/en";
import { ptBR } from "@/i18n/pt_BR";

export type Locale = "en" | "pt-BR";

const TRANSLATIONS: Record<Locale, Record<string, string>> = {
  "en": en,
  "pt-BR": ptBR,
};

const SUPPORTED: ReadonlySet<Locale> = new Set(["en", "pt-BR"]);
const STORAGE_KEY = "agora.locale";

function detectInitialLocale(): Locale {
  if (typeof window === "undefined") return "en";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored && SUPPORTED.has(stored as Locale)) return stored as Locale;
  const nav = window.navigator.language ?? "";
  if (nav.toLowerCase().startsWith("pt")) return "pt-BR";
  return "en";
}

interface I18nState {
  locale: Locale;
  setLocale: (locale: Locale) => void;
}

export const useI18nStore = create<I18nState>((set) => ({
  locale: detectInitialLocale(),
  setLocale: (locale) => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, locale);
    }
    set({ locale });
  },
}));

export function translate(
  locale: Locale,
  key: string,
  fallback?: string,
  vars?: Record<string, string | number>,
): string {
  const template = TRANSLATIONS[locale][key] ?? fallback ?? key;
  if (!vars) return template;
  return template.replace(/\{\{(\w+)\}\}/g, (_, name) =>
    vars[name] !== undefined ? String(vars[name]) : `{{${name}}}`,
  );
}

export type TranslateFn = (
  key: string,
  fallback?: string,
  vars?: Record<string, string | number>,
) => string;

export function useT(): TranslateFn {
  const locale = useI18nStore((s) => s.locale);
  return useCallback<TranslateFn>(
    (key, fallback, vars) => translate(locale, key, fallback, vars),
    [locale],
  );
}

export const SUPPORTED_LOCALES: readonly Locale[] = ["en", "pt-BR"] as const;
