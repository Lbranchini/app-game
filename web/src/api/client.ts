// Thin REST client. Uses Vite's /api proxy in dev and direct paths in prod.

import type { Arena, Character } from "@/types/api";

export interface PlayerProfile {
  id: string;
  provider_subject: string;
  email: string | null;
  name: string | null;
  elo: number;
  unlocked_characters: string[];
  progress: Record<string, number>;
}

export interface MeResponse {
  sub: string;
  email: string | null;
  name: string | null;
  player: PlayerProfile | null;
}

const TOKEN_KEY = "agora.token";

export const auth = {
  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  },
  setToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
  },
  clear(): void {
    localStorage.removeItem(TOKEN_KEY);
  },
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = auth.getToken();
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`/api${path}`, { ...init, headers });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }
  return (await response.json()) as T;
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  listCharacters: () => request<Character[]>("/characters"),
  getCharacter: (id: string) => request<Character>(`/characters/${id}`),
  listArenas: () => request<Arena[]>("/arenas"),
  me: () => request<MeResponse>("/auth/me"),
  devToken: () =>
    request<{ access_token: string; token_type: string }>("/auth/dev-token", {
      method: "POST",
    }),
};
