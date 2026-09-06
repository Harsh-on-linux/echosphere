"use client";

import { AgentVisualizer, type AgentVisualizerState } from "agora-agent-uikit";

type VoiceOrbProps = {
  /** Driven by RTM `state.*` events: listening / thinking / speaking (plan.md 2.2). */
  state: AgentVisualizerState;
  children?: React.ReactNode;
};

/**
 * VoiceOrb — pulses on listening/thinking/speaking states from RTM.
 * Thin wrapper over `AgentVisualizer` so the voice state has one home;
 * `children` hosts the hidden `RemoteUser` audio renderers.
 */
export function VoiceOrb({ state, children }: VoiceOrbProps) {
  return (
    <section
      className="relative flex h-full min-h-[20rem] w-full max-w-4xl flex-col items-center justify-center gap-2"
      aria-label="VaayuMitra voice status"
    >
      <AgentVisualizer state={state} size="lg" />
      <p className="text-xs text-muted-foreground" aria-live="polite">
        {state === "listening"
          ? "Listening…"
          : state === "analyzing"
            ? "Checking IMD…"
            : state === "talking"
              ? "Speaking…"
              : "VaayuMitra"}
      </p>
      {children}
    </section>
  );
}
