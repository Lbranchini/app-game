import { SUPPORTED_LOCALES, useI18nStore, type Locale } from "@/i18n";

const LABEL: Record<Locale, string> = {
  "en": "EN",
  "pt-BR": "PT",
};

export function LanguageSwitcher() {
  const locale = useI18nStore((s) => s.locale);
  const setLocale = useI18nStore((s) => s.setLocale);
  return (
    <div
      role="group"
      aria-label="language"
      className="flex items-center rounded-md bg-slate-800 p-0.5 text-xs ring-1 ring-slate-700"
    >
      {SUPPORTED_LOCALES.map((code) => (
        <button
          key={code}
          type="button"
          onClick={() => setLocale(code)}
          className={[
            "rounded px-2 py-0.5 font-mono transition",
            code === locale
              ? "bg-slate-700 text-slate-100"
              : "text-slate-400 hover:text-slate-200",
          ].join(" ")}
        >
          {LABEL[code]}
        </button>
      ))}
    </div>
  );
}
