import { api } from '../config'
import type { SafetyCheckResponse } from '../../api'

interface SafetyCheckBody {
  command: string
  tool_name?: string
  arguments?: Record<string, unknown>
  affected_resources?: string[]
}

export const useCheckSafety = () => {
  const mutation = api.useMutation<SafetyCheckResponse, Error, SafetyCheckBody>({
    url: '/safety/check',
    method: 'POST',
  })
  return {
    checkSafety: mutation.mutateAsync,
    isChecking: mutation.isPending,
    safetyResult: mutation.data,
    safetyError: mutation.error,
    ...mutation,
  }
}
