import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";

import { api, auth } from "@/api/client";
import { useT } from "@/i18n";

type Status = "idle" | "queued" | "found" | "error";

// A stale "I'm in the queue" marker beyond this window means the server
// almost certainly dropped us; we don't auto-rejoin.
const QUEUE_STICKY_MS = 10 * 60_000;
const QUEUE_STORAGE_KEY = "agora.matchmaking.queuedAt";

export function MatchmakingPage() {
  const t = useT();
  const navigate = useNavigate();
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [queuedAt, setQueuedAt] = useState<number | null>(null);
  const [now, setNow] = useState<number>(() => Date.now());
  const wsRef = useRef<WebSocket | null>(null);
  const me = useQuery({ queryKey: ["me"], queryFn: api.me, refetchInterval: 60_000 });

  useEffect(() => () => wsRef.current?.close(), []);

  // 1Hz tick — only mounted while queued, used for the elapsed counter.
  useEffect(() => {
    if (status !== "queued") return;
    const handle = window.setInterval(() => setNow(Date.now()), 500);
    return () => window.clearInterval(handle);
  }, [status]);

  const join = () => {
    const token = auth.getToken();
    if (!token) {
      setError(t("matchmaking.notAuth"));
      return;
    }
    setError(null);
    setStatus("queued");
    const startedAt = Date.now();
    setQueuedAt(startedAt);
    window.sessionStorage.setItem(QUEUE_STORAGE_KEY, String(startedAt));

    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(
      `${proto}//${window.location.host}/api/matchmaking/ws?token=${encodeURIComponent(token)}`,
    );
    ws.onmessage = (msg) => {
      const frame = JSON.parse(msg.data);
      if (frame.type === "queued") {
        setStatus("queued");
      } else if (frame.type === "match_found") {
        setStatus("found");
        window.sessionStorage.removeItem(QUEUE_STORAGE_KEY);
        navigate(`/draft/${frame.draft_id}?side=${frame.side}`);
      }
    };
    ws.onclose = () => {
      if (status === "queued") setStatus("idle");
    };
    ws.onerror = () => {
      setStatus("error");
      setError(t("matchmaking.wsError"));
    };
    wsRef.current = ws;
  };

  const leave = () => {
    wsRef.current?.send(JSON.stringify({ type: "leave" }));
    setStatus("idle");
    setQueuedAt(null);
    window.sessionStorage.removeItem(QUEUE_STORAGE_KEY);
  };

  // If a recent queue marker survived a reload, auto-rejoin so the player
  // doesn't silently drop out of the queue when refreshing the tab.
  // Runs once on mount; ignored if the marker is stale.
  useEffect(() => {
    const stored = window.sessionStorage.getItem(QUEUE_STORAGE_KEY);
    if (!stored) return;
    const parsed = Number(stored);
    if (!Number.isFinite(parsed) || Date.now() - parsed > QUEUE_STICKY_MS) {
      window.sessionStorage.removeItem(QUEUE_STORAGE_KEY);
      return;
    }
    if (!auth.getToken()) return;  // login handler will route them away anyway
    join();
    // We intentionally re-use the original timestamp so the elapsed counter
    // continues from where it left off.
    setQueuedAt(parsed);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const elapsedSec = queuedAt ? Math.floor((now - queuedAt) / 1000) : 0;
  const elo = me.data?.player?.elo ?? null;

  return (
    <div className="mx-auto max-w-2xl p-8">
      <header className="mb-6">
        <h2 className="text-2xl font-bold">{t("matchmaking.title")}</h2>
        <p className="mt-1 text-sm text-slate-400">{t("matchmaking.tagline")}</p>
      </header>

      <div className="rounded-2xl bg-slate-900/70 p-6 ring-1 ring-slate-800">
        {/* Player chip — always visible so the queue feels personal */}
        {me.data?.player && (
          <div className="mb-5 flex items-center justify-between rounded-lg bg-slate-950/60 px-4 py-3 ring-1 ring-slate-800">
            <div>
              <div className="text-xs uppercase tracking-wider text-slate-500">{t("common.you")}</div>
              <div className="text-sm font-semibold text-slate-100">
                {me.data.player.name ?? me.data.sub}
              </div>
            </div>
            {elo !== null && (
              <div className="text-right">
                <div className="text-xs uppercase tracking-wider text-slate-500">ELO</div>
                <div className="font-mono text-lg font-bold tabular-nums">{elo}</div>
              </div>
            )}
          </div>
        )}

        {status === "idle" && (
          <div className="text-center">
            <p className="mb-4 text-sm text-slate-400">{t("matchmaking.tip")}</p>
            <button
              type="button"
              onClick={join}
              className="rounded-md bg-emerald-600 px-6 py-2.5 font-semibold hover:bg-emerald-500"
            >
              {t("matchmaking.joinQueue")}
            </button>
          </div>
        )}

        {status === "queued" && (
          <div className="text-center">
            <SearchingRipple />
            <p className="mt-2 text-amber-300">{t("matchmaking.searching")}</p>
            <p className="mt-1 font-mono text-3xl font-bold tabular-nums text-slate-100">
              {formatElapsed(elapsedSec)}
            </p>
            <p className="mt-1 text-xs text-slate-500">{t("matchmaking.tipBand")}</p>
            <button
              type="button"
              onClick={leave}
              className="mt-5 rounded-md bg-slate-700 px-5 py-2 text-sm hover:bg-slate-600"
            >
              {t("matchmaking.leaveQueue")}
            </button>
          </div>
        )}

        {status === "found" && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.25 }}
            className="rounded-lg bg-emerald-500/10 px-4 py-6 text-center ring-1 ring-emerald-500/40"
          >
            <p className="text-lg font-semibold text-emerald-300">{t("matchmaking.matchFound")}</p>
            <p className="mt-1 text-xs text-slate-400">{t("matchmaking.routing")}</p>
          </motion.div>
        )}

        {status === "error" && (
          <p className="rounded-lg bg-red-500/10 px-4 py-3 text-center text-sm text-red-300 ring-1 ring-red-500/40">
            {error ?? "Connection error."}
          </p>
        )}

        {status !== "error" && error && (
          <p className="mt-4 text-sm text-red-400">{error}</p>
        )}
      </div>
    </div>
  );
}

function formatElapsed(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function SearchingRipple() {
  return (
    <div className="relative mx-auto h-20 w-20">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="absolute inset-0 rounded-full border-2 border-amber-400/60"
          initial={{ scale: 0.4, opacity: 0.7 }}
          animate={{ scale: 1.4, opacity: 0 }}
          transition={{
            duration: 1.6,
            repeat: Infinity,
            delay: i * 0.45,
            ease: "easeOut",
          }}
        />
      ))}
      <div className="absolute inset-1/4 rounded-full bg-amber-500/30" />
    </div>
  );
}
