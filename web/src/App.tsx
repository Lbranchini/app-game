import { Link, Navigate, Route, Routes } from "react-router-dom";

import { LoginPage } from "@/pages/Login";
import { CharactersPage } from "@/pages/Characters";
import { ArenasPage } from "@/pages/Arenas";
import { BattlePage } from "@/pages/Battle";
import { DraftPage } from "@/pages/Draft";
import { MatchesPage } from "@/pages/Matches";
import { MatchmakingPage } from "@/pages/Matchmaking";
import { useAuthStore } from "@/stores/authStore";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function Header() {
  const { token, clear } = useAuthStore((s) => ({ token: s.token, clear: s.clear }));
  if (!token) return null;
  return (
    <header className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
      <Link to="/characters" className="text-lg font-semibold">
        Agora of Myths
      </Link>
      <nav className="flex gap-4 text-sm">
        <Link to="/characters" className="hover:text-white">Characters</Link>
        <Link to="/arenas" className="hover:text-white">Arenas</Link>
        <Link to="/matchmaking" className="hover:text-white">Play</Link>
        <Link to="/draft" className="hover:text-white">Draft (dev)</Link>
        <Link to="/battle" className="hover:text-white">Battle (dev)</Link>
        <Link to="/matches" className="hover:text-white">Matches</Link>
        <button type="button" onClick={clear} className="hover:text-white">
          Sign out
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
        <Route path="*" element={<Navigate to="/characters" replace />} />
      </Routes>
    </>
  );
}
