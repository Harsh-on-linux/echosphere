import { expect, test } from 'bun:test'

import {
  getAgentLatencySummary,
  getAgentStateLabel,
  normalizeAgentMetric,
  normalizeTranscript,
  normalizeTranscriptSpacing,
} from './conversation'

test('normalizeTranscriptSpacing inserts spaces and collapses whitespace', () => {
  expect(normalizeTranscriptSpacing('Hello.World,now  ok')).toBe('Hello. World, now ok')
})

test("normalizeTranscript remaps uid '0' to the local uid and normalizes text", () => {
  const out = normalizeTranscript(
    [
      { uid: '0', text: 'Hi.There', turn_id: '1', status: 0 },
      { uid: '42', text: 'ok', turn_id: '2', status: 0 },
    ] as any,
    'local-9',
  )
  expect(out[0].uid).toBe('local-9')
  expect(out[0].text).toBe('Hi. There')
  expect(out[1].uid).toBe('42')
})

test('normalizeAgentMetric validates values and normalizes timestamps', () => {
  expect(normalizeAgentMetric({ type: 'LLM', name: 'latency_ms', value: 410, timestamp: 12 })).toEqual({
    type: 'llm',
    name: 'latency_ms',
    value: 410,
    timestamp: 12000,
  })
  expect(normalizeAgentMetric({ type: 'tts', name: 'latency_ms', value: -1, timestamp: 12 })).toBeNull()
})

test('getAgentLatencySummary uses latest metric per pipeline stage', () => {
  const summary = getAgentLatencySummary([
    { type: 'llm', name: 'first', value: 200, timestamp: 1 },
    { type: 'llm', name: 'latest', value: 400, timestamp: 2 },
    { type: 'tts', name: 'speech', value: 300, timestamp: 2 },
    { type: 'context', name: 'ignored', value: 900, timestamp: 2 },
  ])
  expect(summary.totalMs).toBe(700)
  expect(summary.metrics.map((metric) => metric.name)).toEqual(['latest', 'speech'])
  expect(summary.targetMs).toBe(1200)
})

test('getAgentStateLabel provides judge-friendly live state labels', () => {
  expect(getAgentStateLabel('listening')).toBe('Listening')
  expect(getAgentStateLabel('thinking')).toBe('Thinking')
  expect(getAgentStateLabel(null)).toBe('Connecting')
})
