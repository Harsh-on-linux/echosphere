"use client";

import { useEffect, useState } from "react";

type IMDSourceCardProps = {
  /** Phase 3 feeds this: last MCP tool called, district resolved, API timestamp. */
  source?: {
    tool?: string;
    district?: string;
    timestamp?: string;
  } | null;
};

type HealthInfo = {
  imd_cache?: { size?: number; use_mock?: boolean; ttl?: number };
};

/**
 * IMDSourceCard — every weather fact carries IMD `source + timestamp` (plan.md 2.2).
 * Phase 2 shows backend cache/mode attribution; Phase 3 fills `source` per tool call.
 */
export function IMDSourceCard({ source }: IMDSourceCardProps) {
  const [health, setHealth] = useState<HealthInfo | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const response = await fetch("/api/health");
        if (!response.ok) return;
        const data = (await response.json()) as HealthInfo;
        if (!cancelled) setHealth(data);
      } catch {
        // Offline backend: keep static attribution, never block the voice UI.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const useMock = health?.imd_cache?.use_mock;
  const ttl = health?.imd_cache?.ttl;

  return (
    <section
      className="flex w-full flex-col gap-1 rounded-2xl border border-border bg-card/20 px-4 py-3"
      aria-label="IMD data source"
    >
      <h2 className="text-sm font-semibold text-foreground">IMD Source</h2>
      <dl className="flex flex-col gap-1 text-xs text-muted-foreground">
        <div className="flex items-center justify-between gap-2">
          <dt>Tool</dt>
          <dd className="font-medium text-foreground">
            {source?.tool ?? "— (voice loop only)"}
          </dd>
        </div>
        <div className="flex items-center justify-between gap-2">
          <dt>District</dt>
          <dd className="font-medium text-foreground">
            {source?.district ?? "—"}
          </dd>
        </div>
        <div className="flex items-center justify-between gap-2">
          <dt>Updated</dt>
          <dd className="font-medium text-foreground">
            {source?.timestamp ?? "—"}
          </dd>
        </div>
        <div className="flex items-center justify-between gap-2">
          <dt>Mode</dt>
          <dd className="font-medium text-foreground">
            {useMock === undefined
              ? "IMD-grounded"
              : useMock
                ? `IMD sample cache${ttl ? ` · TTL ${ttl}s` : ""}`
                : "IMD live"}
          </dd>
        </div>
      </dl>
      <p className="text-[11px] leading-4 text-muted-foreground">
        Data: India Meteorological Department (api.imd.gov.in). Voice: Agora
        Conversational AI Engine.
      </p>
    </section>
  );
}
