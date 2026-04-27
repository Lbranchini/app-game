import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { auth } from "@/api/client";

type Status = "idle" | "queued" | "found" | "error";

export function MatchmakingPage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => () => wsRef.current?.close(), []);

  const join = () => {
    const token = auth.getToken();
    if (!token) {
      setError("Not authenticated.");
      return;
    }
    setError(null);
    setStatus("queued");

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
        navigate(`/draft/${frame.draft_id}?side=${frame.side}`);
      }
    };
    ws.onclose = () => {
      if (status === "queued") setStatus("idle");
    };
    ws.onerror = () => {
      setStatus("error");
      setError("WebSocket error.");
    };
    wsRef.current = ws;
  };

  const leave = () => {
    wsRef.current?.send(JSON.stringify({ type: "leave" }));
    setStatus("idle");
  };

  return (
    <div className="p-8">
      <h2 className="mb-4 text-2xl font-bold">Ranked queue</h2>
      <p className="mb-6 text-sm text-slate-400">
        Join the queue. The server pairs you with the next player and routes you
        both into a draft.
      </p>

      {status === "idle" && (
        <button
          type="button"
          onClick={join}
          className="rounded-md bg-emerald-600 px-4 py-2 font-medium hover:bg-emerald-500"
        >
          Join queue
        </button>
      )}

      {status === "queued" && (
        <div>
          <p className="mb-3 text-amber-400">Waiting for opponent…</p>
          <button
            type="button"
            onClick={leave}
            className="rounded-md bg-slate-700 px-4 py-2 text-sm hover:bg-slate-600"
          >
            Leave queue
          </button>
        </div>
      )}

      {status === "found" && (
        <p className="text-emerald-400">Match found — redirecting to the draft…</p>
      )}

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
    </div>
  );
}
