import { Award, PlayCircle } from 'lucide-react'
import { useBenchmarkLatest, useRunBenchmark } from '../lib/api/hooks/useBenchmark'

interface BenchmarkReport {
  pass_rate: number
  per_category: Record<string, number>
  signature: string
  results?: Array<{ prompt_id: string; passed: boolean; score: number; notes?: string }>
}

export default function BenchmarkPage() {
  const { benchmark } = useBenchmarkLatest()
  const latest = benchmark as unknown as BenchmarkReport | undefined
  const { runBenchmark, isRunning: running } = useRunBenchmark()

  const trigger = async () => {
    try {
      await runBenchmark()
    } catch {
      // ignore — backend may be running standalone
    }
  }

  return (
    <div style={{ padding: 24, fontFamily: 'ui-sans-serif, system-ui', background: '#0b1020', color: '#e5e7eb', minHeight: '100vh' }}>
      <header style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24, justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Award size={28} color="#a78bfa" />
          <h1 style={{ margin: 0, fontSize: 24 }}>Reasoning Benchmark</h1>
        </div>
        <button
          onClick={trigger}
          disabled={running}
          style={{
            display: 'flex',
            gap: 8,
            alignItems: 'center',
            padding: '10px 18px',
            background: running ? '#475569' : '#7c3aed',
            color: 'white',
            border: 'none',
            borderRadius: 8,
            cursor: running ? 'wait' : 'pointer',
          }}
        >
          <PlayCircle size={18} />
          {running ? 'Running…' : 'Run benchmark'}
        </button>
      </header>

      {!latest && (
        <p style={{ color: '#9ca3af' }}>No benchmark report yet. Click “Run benchmark” to generate one.</p>
      )}

      {latest && (
        <>
          <div style={{ padding: 20, background: '#0f172a', borderRadius: 12, marginBottom: 24 }}>
            <div style={{ fontSize: 12, color: '#9ca3af' }}>Overall pass rate</div>
            <div style={{ fontSize: 48, fontWeight: 800 }}>
              {(latest.pass_rate * 100).toFixed(1)}<span style={{ fontSize: 24, color: '#9ca3af' }}>%</span>
            </div>
            <div style={{ fontSize: 11, color: '#475569', marginTop: 6 }}>signature: {latest.signature}</div>
          </div>

          <section style={{ marginBottom: 24 }}>
            <h2 style={{ fontSize: 16, marginBottom: 12 }}>Per-category pass rate</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10 }}>
              {Object.entries(latest.per_category).map(([cat, rate]) => (
                <div key={cat} style={{ padding: 12, background: '#0f172a', borderRadius: 8 }}>
                  <div style={{ fontSize: 12, color: '#9ca3af' }}>{cat}</div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: rate >= 0.7 ? '#22c55e' : rate >= 0.4 ? '#f59e0b' : '#ef4444' }}>
                    {(rate * 100).toFixed(0)}%
                  </div>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  )
}
