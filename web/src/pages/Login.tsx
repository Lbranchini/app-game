import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "@/api/client";
import { useT } from "@/i18n";
import { useAuthStore } from "@/stores/authStore";

export function LoginPage() {
  const t = useT();
  const setToken = useAuthStore((s) => s.setToken);
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  // Handle redirect-back from the backend OAuth callback. The Google
  // callback sends both `token` (access) and `refresh_token` so the
  // client can rotate without re-OAuthing every 15 minutes.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    const refreshToken = params.get("refresh_token");
    if (token) {
      setToken(token, refreshToken);
      navigate("/characters", { replace: true });
    }
  }, [setToken, navigate]);

  const onProvider = (provider: "google" | "apple") => {
    window.location.href = `/api/auth/${provider}/login`;
  };

  const onDev = async () => {
    try {
      const result = await api.devToken();
      setToken(result.access_token, result.refresh_token ?? undefined);
      navigate("/characters");
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="w-full max-w-sm rounded-2xl bg-slate-800 p-8 shadow-xl">
        <h1 className="mb-6 text-3xl font-bold">{t("nav.brand")}</h1>
        <p className="mb-6 text-sm text-slate-400">{t("login.tagline")}</p>
        <div className="space-y-3">
          <button
            type="button"
            onClick={() => onProvider("google")}
            className="w-full rounded-md bg-white py-2 font-medium text-slate-900 transition hover:bg-slate-100"
          >
            {t("login.continueWithGoogle")}
          </button>
          <button
            type="button"
            onClick={() => onProvider("apple")}
            className="w-full rounded-md bg-black py-2 font-medium text-white transition hover:bg-slate-900"
          >
            {t("login.continueWithApple")}
          </button>
          <div className="pt-4 text-xs text-slate-500">{t("login.localDev")}</div>
          <button
            type="button"
            onClick={onDev}
            className="w-full rounded-md bg-slate-700 py-2 text-sm transition hover:bg-slate-600"
          >
            {t("login.devToken")}
          </button>
        </div>
        {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
      </div>
    </div>
  );
}
