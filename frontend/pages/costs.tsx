import useSWR from 'swr'
import { DollarSign, TrendingUp, AlertCircle } from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_HOST
  ? `https://${process.env.NEXT_PUBLIC_API_HOST}/api/v1`
  : (process.env.NEXT_PUBLIC_API_URL ?? '/api/v1')

const fetcher = (url: string) => fetch(url).then((r) => (r.ok ? r.json() : null))

interface CostSummary {
  total_usd: number
  sessions_over_budget: number
  tracked_sessions: number
  per_model?: Record<string, number>
  anomalies?: Array<{ session_id: string; observed_usd: number; multiplier: number; severity: string }>
  roi?: { total_saved_usd: number; total_cost_usd: number; net_roi_usd: number; roi_ratio: number }
}

export default function CostsPage() {
  const { data } = useSWR<CostSummary>(`${API_BASE}/cost/summary`, fetcher, { refreshInterval: 10_000 })
  const summary = data ?? {
    total_usd: 0,
    sessions_over_budget: 0,
    tracked_sessions: 0,
  }

  return (
    <div style={{ padding: 24, fontFamily: 'ui-sans-serif, system-ui', background: '#0b1020', color: '#e5e7eb', minHeight: '100vh' }}>
      <header style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <DollarSign size={28} color="#fbbf24" />
        <h1 style={{ margin: 0, fontSize: 24 }}>Cost Intelligence</h1>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16, marginBottom: 24 }}>
        <Stat label="Total spend (USD)" value={`$${summary.total_usd.toFixed(2)}`} icon={<DollarSign size={18} />} />
        <Stat label="Tracked sessions" value={summary.tracked_sessions} icon={<TrendingUp size={18} />} />
        <Stat
          label="Over budget"
          value={summary.sessions_over_budget}
          icon={<AlertCircle size={18} color={summary.sessions_over_budget ? '#ef4444' : '#9ca3af'} />}
          tint={summary.sessions_over_budget > 0 ? '#7f1d1d' : undefined}
        />
        {summary.roi && (
          <Stat label="ROI ratio" value={`${summary.roi.roi_ratio.toFixed(1)}×`} icon={<TrendingUp size={18} color="#22c55e" />} />
        )}
      </div>

      {summary.per_model && Object.keys(summary.per_model).length > 0 && (
        <section style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 16, marginBottom: 12 }}>Spend by model</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10 }}>
            {Object.entries(summary.per_model).map(([model, usd]) => (
              <div key={model} style={{ padding: 12, background: '#0f172a', borderRadius: 8 }}>
                <div style={{ fontSize: 12, color: '#9ca3af' }}>{model}</div>
                <div style={{ fontSize: 22, fontWeight: 700 }}>${usd.toFixed(2)}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {summary.anomalies && summary.anomalies.length > 0 && (
        <section>
          <h2 style={{ fontSize: 16, marginBottom: 12 }}>Cost anomalies</h2>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {summary.anomalies.map((a) => (
              <li
                key={a.session_id}
                style={{
                  padding: 12,
                  background: '#0f172a',
                  borderRadius: 8,
                  marginBottom: 8,
                  borderLeft: `4px solid ${a.severity === 'critical' ? '#ef4444' : '#f59e0b'}`,
                  display: 'flex',
                  justifyContent: 'space-between',
                }}
              >
                <span>
                  <strong>{a.session_id}</strong> — {a.multiplier.toFixed(1)}× baseline
                </span>
                <span>${a.observed_usd.toFixed(2)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}

function Stat({
  label,
  value,
  icon,
  tint,
}: {
  label: string
  value: number | string
  icon: React.ReactNode
  tint?: string
}) {
  return (
    <div
      style={{
        padding: 16,
        background: tint ?? '#0f172a',
        borderRadius: 10,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}
    >
      <div>
        <div style={{ fontSize: 12, color: '#9ca3af' }}>{label}</div>
        <div style={{ fontSize: 28, fontWeight: 700, marginTop: 4 }}>{value}</div>
      </div>
      {icon}
    </div>
  )
}
