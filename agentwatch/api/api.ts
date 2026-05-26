/**
 * AgentWatch API Client
 * TypeScript client for the AgentWatch REST API.
 */

const BASE = process.env.NEXT_PUBLIC_API_URL ?? '/api/v1'

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

export type ExecutionStatus =
  | 'pending' | 'running' | 'success' | 'failure'
  | 'blocked' | 'rolled_back' | 'timeout'

export type RiskLevel = 'safe' | 'low' | 'medium' | 'high' | 'critical'

export type EventType = string  // Use specific subtypes where needed

export interface TokenUsage {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  estimated_cost_usd?: number
}

export interface SafetyData {
  risk_level: RiskLevel
  risk_score: number
  blocked: boolean
  reasons: string[]
  matched_policies: string[]
  requires_approval: boolean
}

export interface ToolCallData {
  tool_name: string
  raw_command?: string
  arguments: Record<string, unknown>
  affected_resources: string[]
}

export interface ToolResultData {
  tool_name: string
  output?: string
  error?: string
  execution_time_ms?: number
}

export interface AgentEvent {
  event_id: string
  session_id: string
  agent_id: string
  agent_name?: string
  framework: string
  event_type: EventType
  status: ExecutionStatus
  timestamp: string
  duration_ms?: number
  step_number: number
  goal?: string
  task_id?: string
  tool_call?: ToolCallData
  tool_result?: ToolResultData
  safety?: SafetyData
  token_usage?: TokenUsage
  prompt_preview?: string
  planner_output_preview?: string
  metadata: Record<string, unknown>
  tags: string[]
}

export interface AgentSession {
  session_id: string
  agent_id: string
  agent_name?: string
  framework: string
  started_at: string
  ended_at?: string
  status: ExecutionStatus
  goal?: string
  total_events: number
  total_tokens: number
  estimated_cost_usd: number
  final_confidence?: number
}

export interface ConfidenceResult {
  session_id: string
  overall_score: number
  goal_alignment: number
  consistency_score: number
  anomaly_flags: string[]
  explanation: string
  component_scores: Record<string, number>
}

export interface Checkpoint {
  checkpoint_id: string
  session_id: string
  step_number: number
  checkpoint_type: string
  created_at: string
  snapshot_path?: string
  git_commit_ref?: string
  working_dir?: string
  metadata: Record<string, unknown>
}

export interface DashboardSummary {
  total_sessions: number
  active_sessions: number
  failed_sessions: number
  blocked_sessions: number
  total_tokens: number
  estimated_cost_usd: number
  safety_stats: { checked: number; blocked: number; approved: number }
  event_bus_stats: Record<string, number>
}

export interface ReplayStep {
  index: number
  event: AgentEvent
  annotations: string[]
  is_failure_point: boolean
}

export interface FailureAnalysis {
  primary_cause: string
  contributing_factors: string[]
  first_anomaly_step?: number
  failure_step?: number
  tool_error_counts: Record<string, number>
  repeated_tools: string[]
  blocked_action_count: number
  summary: string
  recommendations: string[]
}

export interface ReplayData {
  session_id: string
  session: AgentSession
  total_events: number
  failure_analysis?: FailureAnalysis
  steps: ReplayStep[]
}

// ─────────────────────────────────────────────
// HTTP helper
// ─────────────────────────────────────────────

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(`AgentWatch API ${res.status}: ${err}`)
  }
  return res.json()
}

// ─────────────────────────────────────────────
// API Methods
// ─────────────────────────────────────────────

export const api = {
  // Health
  health: () => request<{ status: string; version: string }>('/health'.replace('/api/v1', '')),

  // Dashboard
  summary: () => request<DashboardSummary>('/dashboard/summary'),

  // Sessions
  listSessions: (params?: {
    limit?: number
    framework?: string
    status?: string
    since_hours?: number
  }) => {
    const qs = new URLSearchParams()
    if (params?.limit) qs.set('limit', String(params.limit))
    if (params?.framework) qs.set('framework', params.framework)
    if (params?.status) qs.set('status', params.status)
    if (params?.since_hours) qs.set('since_hours', String(params.since_hours))
    return request<{ sessions: AgentSession[]; total: number }>(
      `/sessions${qs.toString() ? `?${qs}` : ''}`
    )
  },

  getSession: (sessionId: string) =>
    request<AgentSession>(`/sessions/${sessionId}`),

  getEvents: (sessionId: string, params?: { event_type?: string; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.event_type) qs.set('event_type', params.event_type)
    if (params?.limit) qs.set('limit', String(params.limit))
    return request<{ session_id: string; events: AgentEvent[]; total: number }>(
      `/sessions/${sessionId}/events${qs.toString() ? `?${qs}` : ''}`
    )
  },

  // Confidence
  getConfidence: (sessionId: string) =>
    request<ConfidenceResult>(`/sessions/${sessionId}/confidence`),

  // Replay
  getReplay: (sessionId: string) =>
    request<ReplayData>(`/sessions/${sessionId}/replay`),

  // Rollback
  getCheckpoints: (sessionId: string) =>
    request<{ session_id: string; checkpoints: Checkpoint[] }>(
      `/sessions/${sessionId}/checkpoints`
    ),

  rollback: (
    sessionId: string,
    body: { checkpoint_id?: string; to_step?: number; restore_filesystem?: boolean; restore_git?: boolean }
  ) =>
    request(`/sessions/${sessionId}/rollback`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  // Safety
  getSafetyPolicy: () => request<Record<string, unknown>>('/safety/policy'),
  updateSafetyPolicy: (policy: Record<string, unknown>) =>
    request('/safety/policy', { method: 'PUT', body: JSON.stringify(policy) }),
  getBlockedEvents: (params?: { limit?: number }) =>
    request<{ blocked_events: AgentEvent[]; total: number }>(
      `/safety/blocked${params?.limit ? `?limit=${params.limit}` : ''}`
    ),
}

// ─────────────────────────────────────────────
// WebSocket hook helper
// ─────────────────────────────────────────────

export function createEventSocket(
  onEvent: (event: AgentEvent) => void,
  wsUrl?: string
): WebSocket {
  const url = wsUrl ?? `ws://${window.location.hostname}:8000/ws/events`
  const ws = new WebSocket(url)

  ws.onmessage = (e) => {
    try {
      const event = JSON.parse(e.data) as AgentEvent
      onEvent(event)
    } catch { /* ignore malformed */ }
  }

  ws.onerror = (e) => console.error('AgentWatch WS error:', e)

  return ws
}
