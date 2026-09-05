"use client";

import { useEffect, useState } from "react";

import {
  clearSnapshots,
  loadSnapshots,
  type SessionSnapshot,
} from "@/lib/sessionHistory";

function formatTime(ms: number): string {
  try {
    return new Date(ms).toLocaleString();
  } catch {
    return String(ms);
  }
}

/**
 * SessionHistoryPanel — plan.md Step 6.2 post-demo analytics.
 * Reads voice-session snapshots (history + turns) persisted to localStorage
 * when each conversation ends. Shown on the pre-call screen for judges.
 */
export function SessionHistoryPanel() {
  const [snapshots, setSnapshots] = useState<SessionSnapshot[]>([]);

  const refresh = () => setSnapshots(loadSnapshots());

  useEffect(() => {
    refresh();
  }, []);

  const handleExport = () => {
    try {
      const blob = new Blob([JSON.stringify(snapshots, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "weathergpt-sessions.json";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch {
      // Export is convenience-only; panel data stays readable.
    }
  };

  const handleClear = () => {
    clearSnapshots();
    refresh();
  };

  if (snapshots.length === 0) {
    return (
      <section
        className="w-full max-w-xl rounded-2xl border border-border bg-card/20 px-4 py-3 text-left"
        aria-label="Past voice sessions"
      >
        <h2 className="text-sm font-semibold text-foreground">Past Sessions</h2>
        <p className="text-xs text-muted-foreground">
          No voice sessions saved yet — start a conversation and its transcript +
          turn metrics will appear here for review.
        </p>
      </section>
    );
  }

  return (
    <section
      className="w-full max-w-xl rounded-2xl border border-border bg-card/20 px-4 py-3 text-left"
      aria-label="Past voice sessions"
    >
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-foreground">
          Past Sessions ({snapshots.length})
        </h2>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={refresh}
            className="text-xs text-muted-foreground underline hover:text-foreground"
          >
            Refresh
          </button>
          <button
            type="button"
            onClick={handleExport}
            className="text-xs text-muted-foreground underline hover:text-foreground"
          >
            Export JSON
          </button>
          <button
            type="button"
            onClick={handleClear}
            className="text-xs text-destructive underline"
          >
            Clear
          </button>
        </div>
      </div>
      <ul className="mt-2 flex max-h-48 flex-col gap-2 overflow-y-auto">
        {snapshots.map((snap, index) => (
          <li
            key={`${snap.agentId}-${snap.endedAt}-${index}`}
            className="rounded-lg border border-border/60 px-3 py-2 text-xs text-muted-foreground"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium text-foreground">
                {formatTime(snap.endedAt)}
              </span>
              <span>
                {Math.max(0, Math.round((snap.endedAt - snap.startedAt) / 1000))}s
              </span>
            </div>
            <div className="mt-0.5 truncate">
              {snap.channel} · {snap.agentId}
              {snap.language ? ` · ${snap.language}` : ""}
              {snap.persona ? ` · ${snap.persona}` : ""}
              {snap.history != null ? " · history ✓" : ""}
              {snap.turns != null ? " · turns ✓" : ""}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
