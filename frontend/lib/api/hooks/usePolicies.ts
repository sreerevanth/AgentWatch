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

/** Payload for updating the policy via the YAML DSL editor. */
interface PolicyYamlPayload {
  yaml: string
}

/** Payload for previewing a policy decision without saving. */
interface PolicyPreviewPayload {
  command: string
  yaml: string
}

/** Raw response from /policies/current — either a structured Policy or a YAML string. */
type PolicyResponse = Policy | string

const policyToYaml = (data: PolicyResponse): string =>
  typeof data === 'string' ? data : `rules: []\n# id: ${data.id}\n# name: ${data.name}\n`

export const usePoliciesCurrent = () => {
  const query = api.useQuery<PolicyResponse>({
    url: '/policies/current',
    key: ['policies', 'current'],
  })
  return {
    policy: query.data,
    policyYaml: query.data != null ? policyToYaml(query.data) : undefined,
    isPolicyLoading: query.isLoading,
    policyError: query.error,
    ...query,
  }
}

export const useUpdatePolicy = () => {
  const mutation = api.useMutation<Policy, Error, PolicyYamlPayload>({
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
  const mutation = api.useMutation<PolicyPreview, Error, PolicyPreviewPayload>({
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
