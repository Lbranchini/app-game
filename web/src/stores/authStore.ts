import { create } from "zustand";

import { auth } from "@/api/client";

interface AuthState {
  token: string | null;
  setToken: (token: string, refreshToken?: string | null) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: auth.getToken(),
  setToken: (token, refreshToken) => {
    auth.setToken(token, refreshToken ?? undefined);
    set({ token });
  },
  clear: () => {
    auth.clear();
    set({ token: null });
  },
}));
