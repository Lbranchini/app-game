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

/** Mirrors the server's `ErrorResponse` envelope (see api/main.py). */
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown> | null;
}

export class ApiRequestError extends Error {
  readonly status: number;
  readonly body: ApiError;

  constructor(status: number, body: ApiError) {
    super(`${body.code}: ${body.message}`);
    this.name = "ApiRequestError";
    this.status = status;
    this.body = body;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = auth.getToken();
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`/api${path}`, { ...init, headers });
  if (!response.ok) {
    // Try to parse the unified ErrorResponse envelope; fall back to plain
    // text if the server (or a proxy) sent something else.
    let body: ApiError;
    try {
      const parsed = (await response.json()) as Partial<ApiError>;
      body = {
        code: parsed.code ?? `http_${response.status}`,
        message: parsed.message ?? response.statusText,
        details: parsed.details ?? null,
      };
    } catch {
      body = {
        code: `http_${response.status}`,
        message: response.statusText || "request failed",
      };
    }
    throw new ApiRequestError(response.status, body);
  }
  return (await response.json()) as T;
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  listCharacters: () => request<Character[]>("/characters"),
  getCharacter: (id: string) => request<Character>(`/characters/${id}`),
  listArenas: () => request<Arena[]>("/arenas"),
  me: () => request<MeResponse>("/auth/me"),
  listUnlockRules: () =>
    request<UnlockRulePayload[]>("/unlocks/rules"),
  devToken: () =>
    request<{ access_token: string; token_type: string }>("/auth/dev-token", {
      method: "POST",
    }),
};

export interface UnlockRulePayload {
  character_id: string;
  description: string;
  progress_key: string | null;
  target: number | null;
}
