import { describe, expect, mock, test } from 'bun:test'

import {
  MAX_SNAPSHOTS,
  SESSION_STORAGE_KEY,
  type SessionSnapshot,
  clearSnapshots,
  loadSnapshots,
  saveSnapshot,
} from './sessionHistory'

function makeSnapshot(id: string): SessionSnapshot {
  return {
    agentId: id,
    channel: 'ch',
    startedAt: 1000,
    endedAt: 2000,
    history: { contents: [] },
    turns: { turns: [] },
  }
}

function withMemoryStorage() {
  const store = new Map<string, string>()
  const getItem = mock((key: string) => (store.has(key) ? store.get(key)! : null))
  const setItem = mock((key: string, value: string) => {
    store.set(key, value)
  })
  const removeItem = mock((key: string) => {
    store.delete(key)
  })
  // @ts-expect-error — stub Math.random-free localStorage for tests
  globalThis.localStorage = { getItem, setItem, removeItem }
  return { store, getItem, setItem, removeItem }
}

describe('sessionHistory', () => {
  test('loadSnapshots returns [] when storage is empty', () => {
    withMemoryStorage()
    expect(loadSnapshots()).toEqual([])
  })

  test('saveSnapshot prepends and loadSnapshots round-trips', () => {
    withMemoryStorage()
    saveSnapshot(makeSnapshot('a1'))
    saveSnapshot(makeSnapshot('a2'))
    const loaded = loadSnapshots()
    expect(loaded.map((s) => s.agentId)).toEqual(['a2', 'a1'])
  })

  test('saveSnapshot caps at MAX_SNAPSHOTS', () => {
    withMemoryStorage()
    for (let i = 0; i < MAX_SNAPSHOTS + 5; i += 1) {
      saveSnapshot(makeSnapshot(`a${i}`))
    }
    expect(loadSnapshots()).toHaveLength(MAX_SNAPSHOTS)
    expect(loadSnapshots()[0].agentId).toBe(`a${MAX_SNAPSHOTS + 4}`)
  })

  test('loadSnapshots ignores corrupt payloads', () => {
    const { store } = withMemoryStorage()
    store.set(SESSION_STORAGE_KEY, 'not-json{')
    expect(loadSnapshots()).toEqual([])
    store.set(SESSION_STORAGE_KEY, JSON.stringify([{ nope: true }, makeSnapshot('ok')]))
    expect(loadSnapshots().map((s) => s.agentId)).toEqual(['ok'])
  })

  test('clearSnapshots removes stored sessions', () => {
    withMemoryStorage()
    saveSnapshot(makeSnapshot('a1'))
    clearSnapshots()
    expect(loadSnapshots()).toEqual([])
  })
})
