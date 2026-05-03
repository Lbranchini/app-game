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
const REFRESH_KEY = "agora.refresh";

export const auth = {
  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  },
  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  },
  setToken(token: string, refreshToken?: string | null): void {
    localStorage.setItem(TOKEN_KEY, token);
    if (refreshToken) {
      localStorage.setItem(REFRESH_KEY, refreshToken);
    }
  },
  clear(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

interface TokenPair {
  access_token: string;
  refresh_token?: string | null;
}

// Single in-flight refresh per browser tab — when several requests 401 at
// once we don't want to fan out N refresh calls (each consuming the JTI
// and racing against the others). The first caller starts the refresh; the
// rest await the same promise.
let inflightRefresh: Promise<string | null> | null = null;

async function tryRefresh(): Promise<string | null> {
  if (inflightRefresh) return inflightRefresh;
  const refresh = auth.getRefreshToken();
  if (!refresh) return null;
  inflightRefresh = (async () => {
    try {
      const resp = await fetch("/api/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!resp.ok) {
        // Refresh itself failed (consumed, expired, server down).
        // Wipe both tokens so the user is forced back through OAuth.
        auth.clear();
        return null;
      }
      const body = (await resp.json()) as TokenPair;
      auth.setToken(body.access_token, body.refresh_token);
      return body.access_token;
    } finally {
      inflightRefresh = null;
    }
  })();
  return inflightRefresh;
}

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

async function request<T>(
  path: string,
  init?: RequestInit,
  options?: { skipRefresh?: boolean },
): Promise<T> {
  const token = auth.getToken();
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`/api${path}`, { ...init, headers });
  if (response.status === 401 && !options?.skipRefresh && auth.getRefreshToken()) {
    // Access token likely expired. Try one refresh and replay the original
    // call. `skipRefresh` guards against an infinite loop if the retry also
    // 401s (or is the refresh call itself).
    const fresh = await tryRefresh();
    if (fresh) {
      return request<T>(path, init, { skipRefresh: true });
    }
  }
  if (!response.ok) {
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
    request<{ access_token: string; refresh_token: string | null; token_type: string }>(
      "/auth/dev-token",
      { method: "POST" },
    ),
};

export interface UnlockRulePayload {
  character_id: string;
  description: string;
  progress_key: string | null;
  target: number | null;
}
