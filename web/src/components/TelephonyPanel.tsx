"use client";

import { useEffect, useState } from "react";

import {
  dialNumber,
  getTelephonyStatus,
  hangupCall,
  type TelephonyStatus,
} from "@/services/api";

/**
 * TelephonyPanel — plan.md Step 6.3 phone-first access.
 * When the Agora Telephony Beta is granted, dial any E.164 number and the
 * callee joins the same VaayuMitra voice loop. Until then the panel shows
 * the enable steps plus the zero-cost phone-bridge fallback (mobile on
 * speaker by the laptop mic), which demos identically for judges.
 */
export function TelephonyPanel() {
  const [status, setStatus] = useState<TelephonyStatus | null>(null);
  const [toNumber, setToNumber] = useState("");
  const [callId, setCallId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const next = await getTelephonyStatus();
        if (!cancelled) setStatus(next);
      } catch {
        if (!cancelled) setStatus(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleDial = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const result = await dialNumber(toNumber.trim());
      setCallId(result.agent_id);
      setMessage(`Calling ${result.to_number}… (${result.status})`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Dial failed");
    } finally {
      setBusy(false);
    }
  };

  const handleHangup = async () => {
    if (!callId) return;
    setBusy(true);
    try {
      await hangupCall(callId);
      setMessage("Call ended.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Hangup failed");
    } finally {
      setCallId(null);
      setBusy(false);
    }
  };

  return (
    <section
      className="w-full max-w-xl rounded-2xl border border-border bg-card/20 px-4 py-3 text-left"
      aria-label="Phone call access"
    >
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-foreground">Phone Call</h2>
        <span
          className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
            status?.enabled
              ? "bg-green-500/15 text-green-600 dark:text-green-400"
              : "bg-muted text-muted-foreground"
          }`}
        >
          {status == null
            ? "checking…"
            : status.enabled
              ? "PSTN live"
              : "Beta not enabled"}
        </span>
      </div>

      {status?.enabled ? (
        <div className="mt-2 flex flex-col gap-2">
          <p className="text-xs text-muted-foreground">
            Dial any number in E.164 format — the callee joins the same IMD-grounded
            voice loop as web callers.
          </p>
          <div className="flex gap-2">
            <input
              type="tel"
              value={toNumber}
              onChange={(e) => setToNumber(e.target.value)}
              placeholder="+919876543210"
              aria-label="Phone number to dial"
              className="min-w-0 flex-1 rounded-lg border border-border bg-background px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground"
            />
            {callId ? (
              <button
                type="button"
                onClick={handleHangup}
                disabled={busy}
                className="rounded-lg bg-destructive px-3 py-1.5 text-sm font-medium text-destructive-foreground disabled:opacity-50"
              >
                Hang up
              </button>
            ) : (
              <button
                type="button"
                onClick={handleDial}
                disabled={busy || toNumber.trim().length === 0}
                className="rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground disabled:opacity-50"
              >
                Dial
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="mt-2 flex flex-col gap-2 text-xs text-muted-foreground">
          <p>
            Direct PSTN needs the Agora Telephony Beta (free, request via Console →
            Talk to Us, mention SIH26068), then set{" "}
            <code className="rounded bg-muted px-1">TELEPHONY_ENABLED=true</code> +{" "}
            <code className="rounded bg-muted px-1">TELEPHONY_FROM_NUMBER</code> and
            redeploy. Backend already exposes{" "}
            <code className="rounded bg-muted px-1">POST /dial</code>,{" "}
            <code className="rounded bg-muted px-1">POST /hangup</code> and{" "}
            <code className="rounded bg-muted px-1">POST /telephonyWebhook</code>.
          </p>
          <p className="rounded-lg border border-border/60 px-3 py-2">
            <span className="font-medium text-foreground">Try today — phone bridge: </span>
            1) Start a conversation on this laptop. 2) Call the laptop from any phone
            on speaker. 3) Hold the phone near the mic — same voice loop, zero PSTN
            cost, proves telephony-first access for feature-phone farmers.
          </p>
        </div>
      )}

      {message ? (
        <p className="mt-2 text-xs text-foreground" role="status">
          {message}
        </p>
      ) : null}
    </section>
  );
}
