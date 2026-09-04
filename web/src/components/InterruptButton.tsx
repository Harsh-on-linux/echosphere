"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { interruptAgent } from "@/services/api";

type InterruptButtonProps = {
  /** Active Agora agent id; button is disabled until the agent joins. */
  agentId?: string;
};

/**
 * InterruptButton — manual interruption demo (plan.md 2.2).
 * Voice interruption is automatic via SoS VAD; this button proves
 * `POST /interruptAgent` cuts the agent within ~300ms on demand.
 */
export function InterruptButton({ agentId }: InterruptButtonProps) {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleInterrupt = async () => {
    if (!agentId || isPending) return;
    setIsPending(true);
    setError(null);
    try {
      await interruptAgent(agentId);
    } catch (nextError) {
      setError(
        nextError instanceof Error ? nextError.message : "Interrupt failed",
      );
    } finally {
      setIsPending(false);
    }
  };

  return (
    <span className="inline-flex items-center gap-2">
      <Button
        variant="outline"
        size="sm"
        className="h-8 rounded-full px-3 text-xs font-medium"
        onClick={handleInterrupt}
        disabled={!agentId || isPending}
        aria-label="Interrupt the speaking agent"
        title="Interrupt agent speech"
      >
        {isPending ? "Interrupting…" : "Interrupt"}
      </Button>
      {error ? (
        <span className="text-xs text-destructive" role="alert">
          {error}
        </span>
      ) : null}
    </span>
  );
}
