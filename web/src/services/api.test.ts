import { afterEach, expect, test } from 'bun:test'

import { dialNumber, getConfig, getCycloneMap, hangupCall, interruptAgent, startAgent, stopAgent } from './api'

const originalFetch = globalThis.fetch
let lastCall: { url: string; init?: RequestInit }

afterEach(() => {
  globalThis.fetch = originalFetch
})

function mockFetch(status: number, body: unknown) {
  globalThis.fetch = (async (url: string | URL, init?: RequestInit) => {
    lastCall = { url: String(url), init }
    return new Response(JSON.stringify(body), {
      status,
      headers: { 'content-type': 'application/json' },
    })
  }) as typeof fetch
}

test('getConfig hits /api/get_config with query and returns data', async () => {
  mockFetch(200, {
    code: 0,
    msg: 'success',
    data: { app_id: 'a', token: 't', uid: '5', channel_name: 'c', agent_uid: '9' },
  })
  const data = await getConfig({ channel: 'c', uid: 5 })
  expect(data.token).toBe('t')
  expect(lastCall.url).toContain('/api/get_config')
  expect(lastCall.url).toContain('channel=c')
  expect(lastCall.url).toContain('uid=5')
})

test('startAgent posts the payload and returns agent_id', async () => {
  mockFetch(200, { code: 0, msg: 'success', data: { agent_id: 'agent-1' } })
  const id = await startAgent('ch', 111, 222)
  expect(id).toBe('agent-1')
  expect(lastCall.url).toContain('/api/startAgent')
  expect(lastCall.init?.method).toBe('POST')
  expect(JSON.parse(String(lastCall.init?.body))).toEqual({
    channelName: 'ch',
    rtcUid: 111,
    userUid: 222,
  })
})

test('startAgent forwards language and persona options', async () => {
  mockFetch(200, { code: 0, msg: 'success', data: { agent_id: 'agent-1' } })
  const id = await startAgent('ch', 111, 222, { language: 'hi-IN', persona: 'farmer' })
  expect(id).toBe('agent-1')
  expect(JSON.parse(String(lastCall.init?.body))).toEqual({
    channelName: 'ch',
    rtcUid: 111,
    userUid: 222,
    language: 'hi-IN',
    persona: 'farmer',
  })
})

test('stopAgent posts the agentId', async () => {
  mockFetch(200, {})
  await stopAgent('agent-1')
  expect(lastCall.url).toContain('/api/stopAgent')
  expect(JSON.parse(String(lastCall.init?.body))).toEqual({ agentId: 'agent-1' })
})

test('interruptAgent posts the agentId', async () => {
  mockFetch(200, {})
  await interruptAgent('agent-1')
  expect(lastCall.url).toContain('/api/interruptAgent')
  expect(lastCall.init?.method).toBe('POST')
  expect(JSON.parse(String(lastCall.init?.body))).toEqual({ agentId: 'agent-1' })
})

test('getConfig throws on an error response', async () => {
  mockFetch(500, { detail: 'boom' })
  await expect(getConfig()).rejects.toThrow('boom')
})

test('getCycloneMap hits /api/cycloneMap and returns the FeatureCollection', async () => {
  const geojson = { type: 'FeatureCollection', features: [], cyclone_name: 'X', source: 'IMD' }
  mockFetch(200, { code: 0, msg: 'success', data: geojson })
  const data = await getCycloneMap()
  expect(data.type).toBe('FeatureCollection')
  expect(data.cyclone_name).toBe('X')
  expect(lastCall.url).toContain('/api/cycloneMap')
})

test('getCycloneMap throws when the envelope is an error', async () => {
  mockFetch(200, { code: 1, msg: 'nope' })
  await expect(getCycloneMap()).rejects.toThrow('nope')
})

test('dialNumber posts toNumber and returns the call', async () => {
  mockFetch(200, {
    code: 0,
    msg: 'success',
    data: { agent_id: 'tel-1', channel_name: 'tel-ch', to_number: '+919876543210', status: 'calling' },
  })
  const result = await dialNumber('+919876543210', { language: 'hi-IN' })
  expect(result.agent_id).toBe('tel-1')
  expect(lastCall.url).toContain('/api/dial')
  expect(JSON.parse(String(lastCall.init?.body))).toEqual({
    toNumber: '+919876543210',
    language: 'hi-IN',
  })
})

test('dialNumber surfaces the Beta-disabled guide', async () => {
  mockFetch(501, { detail: 'Telephony Beta is not enabled. Steps: ...' })
  await expect(dialNumber('+919876543210')).rejects.toThrow('Telephony Beta')
})

test('hangupCall posts the agentId', async () => {
  mockFetch(200, { code: 0, msg: 'success' })
  await hangupCall('tel-1')
  expect(lastCall.url).toContain('/api/hangup')
  expect(JSON.parse(String(lastCall.init?.body))).toEqual({ agentId: 'tel-1' })
})
