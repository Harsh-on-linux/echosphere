'use client'

import {
  type AgentLatencyMetric,
  getAgentLatencySummary,
  getAgentStateLabel,
} from '@/lib/conversation'
import type { AgentState } from 'agora-agent-client-toolkit'

type AgentMetricsOverlayProps = {
  agentState: AgentState | null;
  metrics: AgentLatencyMetric[];
}

const STAGE_LABELS: Record<string, string> = {
  stt: 'ASR',
  asr: 'ASR',
  llm: 'LLM',
  mllm: 'LLM',
  tts: 'TTS',
}

function formatLatency(value: number) {
  return `${Math.round(value)} ms`
}

export function AgentMetricsOverlay({ agentState, metrics }: AgentMetricsOverlayProps) {
  const summary = getAgentLatencySummary(metrics)
  const isWithinTarget = summary.totalMs <= summary.targetMs

  return (
    <section
      className="w-full max-w-xl rounded-xl border border-border bg-card/80 p-3 shadow-sm backdrop-blur-md"
      aria-label='Live agent metrics'
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            Live pipeline</p>
          <p className='mt-1 text-sm font-medium text-foreground' aria-live='polite'>
            Agent {getAgentStateLabel(agentState)}
          </p>
        </div>
        <div className="text-right">
          <p className='text-[11px] uppercase tracking-[0.16em] text-muted-foreground'>Tracked latency</p>
          <p
            className={`mt-1 text-sm font-semibold ${isWithinTarget ? 'text-emerald-500' : 'text-amber-500'}`}
            aria-label={`Tracked latency ${formatLatency(summary.totalMs)}, target ${formatLatency(summary.targetMs)}`}
          >
            {formatLatency(summary.totalMs)}
            <span className='ml-1 text-xs font-normal text-muted-foreground'>
              / {formatLatency(summary.targetMs)} target
            </span>
          </p>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-3 gap-2">
        {summary.metrics.length > 0 ? (
          summary.metrics.map((metric) => (
            <div key={`${metric.type}-${metric.name}`} className="rounded-lg border border-border/80 bg-background/60 px-2 py-2">
              <p className='text-[10px] font-semibold uppercase tracking-wide text-muted-foreground'>
                {STAGE_LABELS[metric.type] ?? metric.type}
              </p>
              <p className='mt-1 truncate text-xs text-foreground' title={metric.name}>
                {metric.name.replace(/[_-]+/g, ' ')}
              </p>
              <p className='mt-1 text-sm font-semibold text-primary'>{formatLatency(metric.value)}</p>
            </div>
          ))
        ) : (
          <p className='col-span-3 text-xs text-muted-foreground'>Waiting for the first Agora metrics event…</p>
        )}
      </div>

      <p className='mt-2 text-[11px] text-muted-foreground'>Agora metrics · ASR + LLM + TTS · target under 1.2s</p>
    </section>
  )
}
