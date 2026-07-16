import { api } from '../config'

interface BenchmarkResult {
  run_id: string
  started_at: string
  completed_at?: string
  status: string
  scores: Record<string, number>
  overall_score: number
  tasks_total: number
  tasks_passed: number
}

export const useBenchmarkLatest = () => {
  const query = api.useQuery<BenchmarkResult>({
    url: '/reasoning/benchmark/latest',
    key: ['benchmark', 'latest'],
  })
  return {
    benchmark: query.data,
    isBenchmarkLoading: query.isLoading,
    benchmarkError: query.error,
    ...query,
  }
}

export const useRunBenchmark = () => {
  const mutation = api.useMutation<BenchmarkResult, Error, void>({
    url: '/reasoning/benchmark/run',
    method: 'POST',
    keyToInvalidate: ['benchmark'],
  })
  return {
    runBenchmark: mutation.mutateAsync,
    isRunning: mutation.isPending,
    ...mutation,
  }
}
