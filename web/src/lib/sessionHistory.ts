/**
 * Session snapshots — plan.md Step 6.2 persistence.
 * After each voice session ends, the app stores /agentHistory + /agentTurns
 * in localStorage (cap 20) for post-demo analytics. No backend or Supabase
 * needed for the hackathon; best-effort and never blocks the voice UI.
 */

export type SessionSnapshot = {
  agentId: string
  channel: string
  startedAt: number
  endedAt: number
  language?: string
  persona?: string
  history: unknown
  turns: unknown
}

export const SESSION_STORAGE_KEY = 'weathergpt.sessions.v1'
export const MAX_SNAPSHOTS = 20

function storage(): Storage | null {
  try {
    if (typeof localStorage === 'undefined') return null
    return localStorage
  } catch {
    return null
  }
}

export function loadSnapshots(): SessionSnapshot[] {
  const store = storage()
  if (!store) return []
  try {
    const raw = store.getItem(SESSION_STORAGE_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter(
      (item): item is SessionSnapshot =>
        !!item &&
        typeof item === 'object' &&
        typeof (item as SessionSnapshot).agentId === 'string',
    )
  } catch {
    return []
  }
}

export function saveSnapshot(snapshot: SessionSnapshot): SessionSnapshot[] {
  const next = [snapshot, ...loadSnapshots()].slice(0, MAX_SNAPSHOTS)
  try {
    storage()?.setItem(SESSION_STORAGE_KEY, JSON.stringify(next))
  } catch {
    // Quota or private mode: keep voice flow unaffected.
  }
  return next
}

export function clearSnapshots(): void {
  try {
    storage()?.removeItem(SESSION_STORAGE_KEY)
  } catch {
    // Best-effort only.
  }
}
