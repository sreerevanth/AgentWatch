import { Shield, ShieldAlert } from 'lucide-react'
import { useOwaspScan } from '../lib/api/hooks/useSecurity'

const SEVERITY_COLORS: Record<string, string> = {
  low: '#10b981',
  medium: '#f59e0b',
  high: '#f97316',
  critical: '#ef4444',
}

export default function SecurityPage() {
  const { owaspScan, isOwaspLoading: isLoading, owaspError } = useOwaspScan()
  const findings = owaspScan?.findings ?? []
  const score = owaspScan?.score ?? null
  const scoreKnown = !isLoading && !owaspError && score !== null
  const shieldColor = isLoading || owaspError || score === null
    ? '#9ca3af'
    : score >= 80 ? '#22c55e' : score >= 60 ? '#f59e0b' : '#ef4444'

  const byVector = findings.reduce<Record<string, number>>((acc, f) => {
    acc[f.vector] = (acc[f.vector] ?? 0) + 1
    return acc
  }, {})

  return (
    <div style={{ padding: 24, fontFamily: 'ui-sans-serif, system-ui', background: '#0b1020', color: '#e5e7eb', minHeight: '100vh' }}>
      <header style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <Shield size={28} color={shieldColor} />
        <h1 style={{ margin: 0, fontSize: 24 }}>OWASP Agentic Top 10</h1>
      </header>

      {owaspError ? (
        <div style={{ padding: 20, background: '#1e0a0a', border: '1px solid #ef444440', borderRadius: 12, marginBottom: 24, color: '#fca5a5' }}>
          Failed to load OWASP scan results. Check backend connectivity and try again.
        </div>
      ) : (
        <div style={{ padding: 20, background: '#0f172a', borderRadius: 12, marginBottom: 24 }}>
          <div style={{ fontSize: 12, color: '#9ca3af' }}>Security score</div>
          <div style={{ fontSize: 48, fontWeight: 800, color: shieldColor }}>
            {isLoading ? '—' : scoreKnown ? score : '—'}
          </div>
          <div style={{ fontSize: 12, color: '#9ca3af' }}>{isLoading ? 'Loading…' : scoreKnown ? `${findings.length} finding${findings.length === 1 ? '' : 's'}` : 'No scan data'}</div>
        </div>
      )}

      {!isLoading && Object.keys(byVector).length > 0 && (
        <section style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 16, marginBottom: 12 }}>Findings by vector</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10 }}>
            {(Object.entries(byVector) as [string, number][]).map(([v, count]) => (
              <div key={v} style={{ padding: 12, background: '#0f172a', borderRadius: 8 }}>
                <div style={{ fontSize: 12, color: '#9ca3af' }}>{v}</div>
                <div style={{ fontSize: 22, fontWeight: 700 }}>{count}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section>
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>All findings</h2>
        {isLoading && <p style={{ color: '#9ca3af' }}>Scanning…</p>}
        {!isLoading && !owaspError && findings.length === 0 && (
          <p style={{ color: '#22c55e' }}>No findings. Sessions look clean.</p>
        )}
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {findings.map((f, i) => (
            <li
              key={i}
              style={{
                padding: 12,
                background: '#0f172a',
                borderRadius: 8,
                marginBottom: 8,
                borderLeft: `4px solid ${SEVERITY_COLORS[f.severity] ?? '#9ca3af'}`,
                display: 'flex',
                gap: 12,
                alignItems: 'center',
              }}
            >
              <ShieldAlert size={18} color={SEVERITY_COLORS[f.severity]} />
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600 }}>{f.vector}</div>
                <div style={{ fontSize: 12, color: '#94a3b8' }}>{f.detail}</div>
              </div>
              <span
                style={{
                  fontSize: 11,
                  padding: '2px 8px',
                  borderRadius: 4,
                  background: SEVERITY_COLORS[f.severity] ?? '#9ca3af',
                  color: 'white',
                  textTransform: 'uppercase',
                }}
              >
                {f.severity}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
