import {
  type AgentState,
  type AgentTranscription,
  type TranscriptHelperItem,
  TurnStatus,
  type UserTranscription,
} from 'agora-agent-client-toolkit'
import type { AgentVisualizerState, IMessageListItem } from 'agora-agent-uikit'

export type AgentLatencyMetric = {
  type: string
  name: string
  value: number
  timestamp: number
}

export type AgentLatencySummary = {
  metrics: AgentLatencyMetric[]
  totalMs: number
  targetMs: number
}

export function normalizeTranscriptSpacing(text: string): string {
  return text
    .replace(/([.!?])([A-Za-z])/g, '$1 $2')
    .replace(/,([A-Za-z])/g, ', $1')
    .replace(/\s{2,}/g, ' ')
    .trim()
}

export function normalizeTimestampMs(timestamp: number): number {
  return timestamp > 1e12 ? timestamp : timestamp * 1000
}

export function normalizeAgentMetric(metric: Partial<AgentLatencyMetric>): AgentLatencyMetric | null {
  if (typeof metric.type !== 'string' || typeof metric.name !== 'string') return null
  if (typeof metric.value !== 'number' || !Number.isFinite(metric.value) || metric.value < 0) return null
  if (typeof metric.timestamp !== 'number' || !Number.isFinite(metric.timestamp)) return null

  return {
    type: metric.type.toLowerCase(),
    name: metric.name,
    value: metric.value,
    timestamp: normalizeTimestampMs(metric.timestamp),
  }
}

export function getAgentLatencySummary(
  metrics: AgentLatencyMetric[],
  targetMs = 1200,
): AgentLatencySummary {
  const latestByStage = new Map<string, AgentLatencyMetric>()
  const stageForType: Record<string, string> = {
    stt: 'asr',
    asr: 'asr',
    llm: 'llm',
    mllm: 'llm',
    tts: 'tts',
  }
  for (const metric of metrics) {
    const stage = stageForType[metric.type.toLowerCase()]
    if (stage) latestByStage.set(stage, metric)
  }

  const trackedTypes = ['asr', 'llm', 'tts']
  const trackedMetrics: AgentLatencyMetric[] = []
  for (const type of trackedTypes) {
    const metric = latestByStage.get(type)
    if (metric) trackedMetrics.push(metric)
  }

  return {
    metrics: trackedMetrics,
    totalMs: trackedMetrics.reduce((total, metric) => total + metric.value, 0),
    targetMs,
  }
}

export function getAgentStateLabel(state: AgentState | null): string {
  switch (state) {
    case 'listening':
      return 'Listening'
    case 'thinking':
      return 'Thinking'
    case 'speaking':
      return 'Speaking'
    case 'silent':
      return 'Silent'
    case 'idle':
      return 'Idle'
    default:
      return 'Connecting'
  }
}

export function mapAgentVisualizerState(
  agentState: AgentState | null,
  isAgentConnected: boolean,
  connectionState: string,
): AgentVisualizerState {
  if (connectionState === 'DISCONNECTED' || connectionState === 'DISCONNECTING') {
    return 'disconnected'
  }

  if (connectionState === 'CONNECTING' || connectionState === 'RECONNECTING') {
    return 'joining'
  }

  if (!isAgentConnected) {
    return 'not-joined'
  }

  switch (agentState) {
    case 'listening':
      return 'listening'
    case 'thinking':
      return 'analyzing'
    case 'speaking':
      return 'talking'
    default:
      return 'ambient'
  }
}

function toMessageListItem(
  item: TranscriptHelperItem<Partial<UserTranscription | AgentTranscription>>,
): IMessageListItem {
  return {
    turn_id: item.turn_id,
    uid: Number(item.uid) || 0,
    text: typeof item.text === 'string' ? item.text : '',
    status: item.status as unknown as IMessageListItem['status'],
    createdAt:
      typeof item._time === 'number'
        ? normalizeTimestampMs(item._time)
        : undefined,
  }
}

export function normalizeTranscript(
  transcript: TranscriptHelperItem<Partial<UserTranscription | AgentTranscription>>[],
  localUid: string,
) {
  return transcript.map((item) => {
    const nextUid = item.uid === '0' ? localUid : item.uid
    const nextText =
      typeof item.text === 'string' ? normalizeTranscriptSpacing(item.text) : item.text

    return { ...item, uid: nextUid, text: nextText }
  })
}

export function getMessageList(
  transcript: TranscriptHelperItem<Partial<UserTranscription | AgentTranscription>>[],
) {
  return transcript
    .filter((item) => item.status !== TurnStatus.IN_PROGRESS)
    .map(toMessageListItem)
}

export function getCurrentInProgressMessage(
  transcript: TranscriptHelperItem<Partial<UserTranscription | AgentTranscription>>[],
) {
  const item = transcript.find((entry) => entry.status === TurnStatus.IN_PROGRESS)
  return item ? toMessageListItem(item) : null
}
