import { api } from '../config'

interface Policy {
  id: string
  name: string
  rules: Array<{ condition: string; action: string; priority: number }>
  enabled: boolean
  updated_at: string
}

interface PolicyPreview {
  would_block: boolean
  matched_rules: string[]
  risk_assessment: string
}

export const usePoliciesCurrent = () => {
  const query = api.useQuery<Policy>({
    url: '/policies/current',
    key: ['policies', 'current'],
  })
  return {
    policy: query.data,
    isPolicyLoading: query.isLoading,
    policyError: query.error,
    ...query,
  }
}

export const useUpdatePolicy = () => {
  const mutation = api.useMutation<Policy, Error, Partial<Policy>>({
    url: '/policies/current',
    method: 'PUT',
    keyToInvalidate: ['policies'],
  })
  return {
    updatePolicy: mutation.mutateAsync,
    isUpdating: mutation.isPending,
    ...mutation,
  }
}

export const usePreviewPolicy = () => {
  const mutation = api.useMutation<PolicyPreview, Error, { command: string; policy: Partial<Policy> }>({
    url: '/policies/preview',
    method: 'POST',
  })
  return {
    previewPolicy: mutation.mutateAsync,
    isPreviewing: mutation.isPending,
    previewResult: mutation.data,
    ...mutation,
  }
}
