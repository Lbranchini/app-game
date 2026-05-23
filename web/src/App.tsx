import { Link, Navigate, Route, Routes } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { useT } from "@/i18n";
import { LoginPage } from "@/pages/Login";
import { CharactersPage } from "@/pages/Characters";
import { ArenasPage } from "@/pages/Arenas";
import { BattlePage } from "@/pages/Battle";
import { DraftPage } from "@/pages/Draft";
import { HelpPage } from "@/pages/Help";
import { MatchesPage } from "@/pages/Matches";
import { MatchmakingPage } from "@/pages/Matchmaking";
import { ProfilePage } from "@/pages/Profile";
import { useAuthStore } from "@/stores/authStore";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function Header() {
  const t = useT();
  const { token, clear } = useAuthStore((s) => ({ token: s.token, clear: s.clear }));
  const profile = useQuery({
    queryKey: ["me"],
    queryFn: api.me,
    enabled: Boolean(token),
    refetchInterval: 30_000,
  });
  if (!token) return null;
  const player = profile.data?.player;
  const displayName = player?.name ?? profile.data?.name ?? profile.data?.sub ?? t("common.you");
  return (
    <header className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
      <Link to="/characters" className="text-lg font-semibold">
        {t("nav.brand")}
      </Link>
      <nav className="flex items-center gap-4 text-sm">
        <Link to="/characters" className="hover:text-white">{t("nav.characters")}</Link>
        <Link to="/arenas" className="hover:text-white">{t("nav.arenas")}</Link>
        <Link to="/matchmaking" className="hover:text-white">{t("nav.play")}</Link>
        <Link to="/draft" className="hover:text-white">{t("nav.draft")}</Link>
        <Link to="/battle" className="hover:text-white">{t("nav.battle")}</Link>
        <Link to="/matches" className="hover:text-white">{t("nav.matches")}</Link>
        <Link to="/profile" className="hover:text-white">{t("nav.profile")}</Link>
        <Link to="/help" className="hover:text-white">{t("nav.help")}</Link>
        <span className="ml-4 rounded-md bg-slate-800 px-3 py-1 text-xs text-slate-300">
          {displayName}
          {player && (
            <>
              {" · "}
              <span className="text-emerald-400">{t("nav.elo", undefined, { elo: player.elo })}</span>
            </>
          )}
        </span>
        <LanguageSwitcher />
        <button type="button" onClick={clear} className="hover:text-white">
          {t("nav.signOut")}
        </button>
      </nav>
    </header>
  );
}

export function App() {
  return (
    <>
      <Header />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/characters"
          element={
            <RequireAuth>
              <CharactersPage />
            </RequireAuth>
          }
        />
        <Route
          path="/arenas"
          element={
            <RequireAuth>
              <ArenasPage />
            </RequireAuth>
          }
        />
        <Route
          path="/battle"
          element={
            <RequireAuth>
              <BattlePage />
            </RequireAuth>
          }
        />
        <Route
          path="/battle/:matchId"
          element={
            <RequireAuth>
              <BattlePage />
            </RequireAuth>
          }
        />
        <Route
          path="/draft"
          element={
            <RequireAuth>
              <DraftPage />
            </RequireAuth>
          }
        />
        <Route
          path="/draft/:draftId"
          element={
            <RequireAuth>
              <DraftPage />
            </RequireAuth>
          }
        />
        <Route
          path="/matchmaking"
          element={
            <RequireAuth>
              <MatchmakingPage />
            </RequireAuth>
          }
        />
        <Route
          path="/matches"
          element={
            <RequireAuth>
              <MatchesPage />
            </RequireAuth>
          }
        />
        <Route
          path="/help"
          element={
            <RequireAuth>
              <HelpPage />
            </RequireAuth>
          }
        />
        <Route
          path="/profile"
          element={
            <RequireAuth>
              <ProfilePage />
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/characters" replace />} />
      </Routes>
    </>
  );
}
