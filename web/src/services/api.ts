const API_BASE_URL = '/api'

export interface GetConfigResponse {
  app_id: string
  token: string
  uid: string
  channel_name: string
  agent_uid: string
}

export async function getConfig(options?: { channel?: string; uid?: string | number }): Promise<GetConfigResponse> {
  const params = new URLSearchParams()
  if (options?.channel !== undefined && options.channel !== '') {
    params.set('channel', options.channel)
  }
  if (options?.uid !== undefined && options.uid !== '') {
    params.set('uid', String(options.uid))
  }

  const query = params.toString()
  const response = await fetch(`${API_BASE_URL}/get_config${query ? `?${query}` : ''}`, {
    method: 'GET',
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  const result = await response.json()
  if (result.code !== 0 || !result.data) {
    throw new Error(result.msg || 'Failed to get configuration')
  }
  return result.data
}

export interface TokenResponse {
  rtcToken: string
  rtmToken: string
  channel: string
  uid: string
  app_id: string
}

export async function getToken(options?: { channel?: string; uid?: string | number }): Promise<TokenResponse> {
  const response = await fetch(`${API_BASE_URL}/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ channel: options?.channel, uid: options?.uid ? Number(options.uid) : undefined }),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || `HTTP ${response.status}`)
  }
  return response.json()
}

export async function startAgent(
  channelName: string,
  rtcUid: number,
  userUid: number,
  options?: { language?: string; persona?: string },
): Promise<string> {
  const payload: Record<string, unknown> = { channelName, rtcUid, userUid }
  if (options?.language) payload.language = options.language
  if (options?.persona) payload.persona = options.persona

  const response = await fetch(`${API_BASE_URL}/startAgent`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  const result = await response.json()
  if (result.code !== 0 || !result.data?.agent_id) {
    throw new Error(result.msg || 'Failed to start agent')
  }
  return result.data.agent_id
}

export async function stopAgent(agentId: string): Promise<void> {
  if (!agentId) return

  const response = await fetch(`${API_BASE_URL}/stopAgent`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agentId }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || `HTTP ${response.status}`)
  }
}

export async function interruptAgent(agentId: string): Promise<void> {
  if (!agentId) return

  const response = await fetch(`${API_BASE_URL}/interruptAgent`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agentId }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || `HTTP ${response.status}`)
  }
}

export async function getAgentHistory(agentId: string): Promise<unknown> {
  const response = await fetch(
    `${API_BASE_URL}/agentHistory?agentId=${encodeURIComponent(agentId)}`,
    { method: 'GET' },
  )

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || `HTTP ${response.status}`)
  }
  return response.json()
}

export async function getAgentTurns(
  agentId: string,
  options?: { pageIndex?: number; pageSize?: number },
): Promise<unknown> {
  const params = new URLSearchParams({ agentId })
  if (options?.pageIndex !== undefined) params.set('pageIndex', String(options.pageIndex))
  if (options?.pageSize !== undefined) params.set('pageSize', String(options.pageSize))

  const response = await fetch(`${API_BASE_URL}/agentTurns?${params.toString()}`, {
    method: 'GET',
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || `HTTP ${response.status}`)
  }
  return response.json()
}

export interface CycloneMapFeature {
  type: 'Feature'
  geometry: { type: string; coordinates: unknown }
  properties: { kind: string; name?: string | null; category?: string; msw_kts?: number }
}

export interface CycloneMapData {
  type: 'FeatureCollection'
  features: CycloneMapFeature[]
  cyclone_name: string | null
  source: string
  cached_at?: string
}

export async function getCycloneMap(): Promise<CycloneMapData> {
  const response = await fetch(`${API_BASE_URL}/cycloneMap`, { method: 'GET' })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  const result = await response.json()
  if (result.code !== 0 || !result.data) {
    throw new Error(result.msg || 'Failed to load cyclone map')
  }
  return result.data as CycloneMapData
}
