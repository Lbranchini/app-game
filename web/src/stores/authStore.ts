import { create } from "zustand";

import { auth } from "@/api/client";

interface AuthState {
  token: string | null;
  setToken: (token: string) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: auth.getToken(),
  setToken: (token) => {
    auth.setToken(token);
    set({ token });
  },
  clear: () => {
    auth.clear();
    set({ token: null });
  },
}));
