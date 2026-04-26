import { Link, Navigate, Route, Routes } from "react-router-dom";

import { LoginPage } from "@/pages/Login";
import { CharactersPage } from "@/pages/Characters";
import { ArenasPage } from "@/pages/Arenas";
import { BattlePage } from "@/pages/Battle";
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
        <Link to="/battle" className="hover:text-white">Battle</Link>
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
        <Route path="*" element={<Navigate to="/characters" replace />} />
      </Routes>
    </>
  );
}
