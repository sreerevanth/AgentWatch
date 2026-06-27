import { createApiClient } from 'react-query-ease'

const BASE = process.env.NEXT_PUBLIC_API_HOST
  ? `https://${process.env.NEXT_PUBLIC_API_HOST}/api/v1`
  : (process.env.NEXT_PUBLIC_API_URL ?? '/api/v1')

export const api = createApiClient({ baseURL: BASE })
