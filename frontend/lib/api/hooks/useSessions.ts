import { api } from '../config'
import type { AgentSession, AgentEvent, FailureAnalysis, ReplayStep } from '../../api'

interface Checkpoint {
  checkpoint_id: string
  step_number: number
  created_at: string
  label?: string
}

interface RollbackBody {
  sessionId: string
  checkpoint_id?: string
  to_step?: number
  restore_filesystem?: boolean
  restore_git?: boolean
}

interface SimulateBody {
  sessionId: string
  rewind_to_step: number
  tool_id?: string
  replacement?: string
  notes?: string
}

export const useSession = (id: string | undefined) => {
  const query = api.useQuery<AgentSession>({
    url: `/sessions/${id}`,
    key: ['sessions', id],
    enabled: !!id,
  })
  return {
    session: query.data,
    isSessionLoading: query.isLoading,
    sessionError: query.error,
    ...query,
  }
}

export const useSessionReplay = (id: string | undefined) => {
  const query = api.useQuery<{ steps: ReplayStep[]; failure_analysis?: FailureAnalysis }>({
    url: `/sessions/${id}/replay`,
    key: ['sessions', id, 'replay'],
    enabled: !!id,
  })
  return {
    replay: query.data,
    isReplayLoading: query.isLoading,
    replayError: query.error,
    ...query,
  }
}

export const useSessionConfidence = (id: string | undefined) => {
  const query = api.useQuery<{ confidence: number; overall_score: number; breakdown: Record<string, number> }>({
    url: `/sessions/${id}/confidence`,
    key: ['sessions', id, 'confidence'],
    enabled: !!id,
  })
  return {
    confidence: query.data,
    isConfidenceLoading: query.isLoading,
    ...query,
  }
}

export const useSessionCheckpoints = (id: string | undefined) => {
  const query = api.useQuery<Checkpoint[]>({
    url: `/sessions/${id}/checkpoints`,
    key: ['sessions', id, 'checkpoints'],
    enabled: !!id,
  })
  return {
    checkpoints: query.data ?? [],
    isCheckpointsLoading: query.isLoading,
    ...query,
  }
}

export const useRollback = () => {
  const mutation = api.useMutation<void, Error, RollbackBody>({
    url: (vars) => `/sessions/${vars.sessionId}/rollback`,
    method: 'POST',
    keyToInvalidate: ['sessions'],
  })
  return {
    rollback: mutation.mutateAsync,
    isRollingBack: mutation.isPending,
    ...mutation,
  }
}

export interface SimulationResult {
  session_id: string
  diverged_at_step: number | null
  original_events: AgentEvent[]
  alternate_events: AgentEvent[]
  summary: string
}

export const useSimulate = () => {
  const mutation = api.useMutation<SimulationResult, Error, SimulateBody>({
    url: (vars) => `/sessions/${vars.sessionId}/simulate`,
    method: 'POST',
  })
  return {
    simulate: mutation.mutateAsync,
    isSimulating: mutation.isPending,
    ...mutation,
  }
}
