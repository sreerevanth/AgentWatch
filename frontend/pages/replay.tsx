import { useEffect, useMemo, useState } from 'react'
import useSWR from 'swr'
import { useRouter } from 'next/router'
import { Play, Pause, ChevronLeft, ChevronRight, SkipBack, SkipForward, Rewind, Film } from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_HOST
  ? `https://${process.env.NEXT_PUBLIC_API_HOST}/api/v1`
  : (process.env.NEXT_PUBLIC_API_URL ?? '/api/v1')

const fetcher = (url: string) => fetch(url).then((r) => (r.ok ? r.json() : null))

interface ReplayEvent {
  event_id: string
  event_type: string
  step_number: number
  timestamp: string
  status: string
  tool_call?: { tool_name: string; raw_command?: string; arguments?: Record<string, unknown> }
  tool_result?: { tool_name: string; output?: string; error?: string }
  planner_output_preview?: string
  safety?: { risk_level: string; risk_score: number; reasons: string[] }
}

interface ReplaySession {
  session_id: string
  goal?: string
  events: ReplayEvent[]
  total_events: number
}

const EVENT_COLOR: Record<string, string> = {
  'tool.call': '#3b82f6',
  'tool.result': '#22c55e',
  'tool.error': '#ef4444',
  'planner.output': '#a78bfa',
  'planner.input': '#a78bfa',
  'safety.block': '#dc2626',
  'session.start': '#6b7280',
  'session.end': '#6b7280',
  'agent.start': '#6b7280',
  'agent.end': '#6b7280',
}

export default function ReplayPage() {
  const router = useRouter()
  const sessionParam = typeof router.query.session === 'string' ? router.query.session : ''
  const tokenParam = typeof router.query.token === 'string' ? router.query.token : ''

  const url = tokenParam
    ? `${API_BASE}/share/${tokenParam}`
    : sessionParam
    ? `${API_BASE}/sessions/${sessionParam}/replay`
    : null
  const { data, isLoading } = useSWR<ReplaySession>(url, fetcher)
  const events: ReplayEvent[] = data?.events ?? []

  const [step, setStep] = useState(0)
  const [playing, setPlaying] = useState(false)

  useEffect(() => {
    if (!playing || events.length === 0) return
    if (step >= events.length - 1) {
      setPlaying(false)
      return
    }
    const t = setTimeout(() => setStep((s) => Math.min(s + 1, events.length - 1)), 700)
    return () => clearTimeout(t)
  }, [playing, step, events.length])

  const current = events[step]

  const goalLabel = useMemo(() => data?.goal ?? '', [data])

  return (
    <div style={{ padding: 24, fontFamily: 'ui-sans-serif, system-ui', background: '#0b1020', color: '#e5e7eb', minHeight: '100vh' }}>
      <header style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <Film size={28} color="#f472b6" />
        <h1 style={{ margin: 0, fontSize: 24 }}>Replay Studio</h1>
      </header>

      {!url && (
        <p style={{ color: '#9ca3af' }}>
          Open <code>/replay?session=&lt;id&gt;</code> or <code>/replay?token=&lt;share_token&gt;</code> to view a session.
        </p>
      )}

      {isLoading && url && <p style={{ color: '#9ca3af' }}>Loading session…</p>}

      {data && (
        <>
          {goalLabel && <p style={{ color: '#94a3b8', marginBottom: 12 }}>Goal: <strong>{goalLabel}</strong></p>}

          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
            <button onClick={() => setStep(0)} style={btn}><SkipBack size={16} /></button>
            <button onClick={() => setStep((s) => Math.max(0, s - 5))} style={btn}><Rewind size={16} /></button>
            <button onClick={() => setStep((s) => Math.max(0, s - 1))} style={btn}><ChevronLeft size={16} /></button>
            <button onClick={() => setPlaying((p) => !p)} style={{ ...btn, background: '#7c3aed' }}>
              {playing ? <Pause size={16} /> : <Play size={16} />}
              {playing ? 'Pause' : 'Play'}
            </button>
            <button onClick={() => setStep((s) => Math.min(events.length - 1, s + 1))} style={btn}><ChevronRight size={16} /></button>
            <button onClick={() => setStep(events.length - 1)} style={btn}><SkipForward size={16} /></button>
            <span style={{ marginLeft: 'auto', fontSize: 13, color: '#94a3b8' }}>
              Step {events.length === 0 ? 0 : step + 1} / {events.length}
            </span>
          </div>

          <input
            type="range"
            min={0}
            max={Math.max(0, events.length - 1)}
            value={step}
            onChange={(e) => setStep(Number(e.target.value))}
            style={{ width: '100%', marginBottom: 24 }}
          />

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 16 }}>
            <aside style={{ background: '#0f172a', borderRadius: 10, padding: 12, maxHeight: '70vh', overflowY: 'auto' }}>
              {events.map((ev, i) => (
                <button
                  key={ev.event_id}
                  onClick={() => setStep(i)}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    padding: 8,
                    marginBottom: 4,
                    background: i === step ? '#1e293b' : 'transparent',
                    border: 'none',
                    borderLeft: `3px solid ${EVENT_COLOR[ev.event_type] ?? '#475569'}`,
                    color: '#e5e7eb',
                    cursor: 'pointer',
                    borderRadius: 4,
                  }}
                >
                  <div style={{ fontSize: 11, color: '#94a3b8' }}>step {ev.step_number}</div>
                  <div style={{ fontSize: 13 }}>{ev.event_type}</div>
                </button>
              ))}
            </aside>

            <main style={{ background: '#0f172a', borderRadius: 10, padding: 20 }}>
              {current ? (
                <>
                  <div style={{ fontSize: 12, color: '#94a3b8', textTransform: 'uppercase' }}>
                    {current.event_type}
                  </div>
                  <h2 style={{ marginTop: 4 }}>{current.tool_call?.tool_name ?? current.event_type}</h2>
                  <div style={{ fontSize: 12, color: '#64748b', marginBottom: 16 }}>
                    {new Date(current.timestamp).toLocaleString()}
                  </div>

                  {current.tool_call?.raw_command && (
                    <pre style={{ background: '#020617', padding: 12, borderRadius: 6, fontSize: 13, overflow: 'auto' }}>
                      {current.tool_call.raw_command}
                    </pre>
                  )}

                  {current.tool_result?.output !== undefined && (
                    <>
                      <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 12, marginBottom: 4 }}>Output</div>
                      <pre style={{ background: '#020617', padding: 12, borderRadius: 6, fontSize: 13, overflow: 'auto', maxHeight: 240 }}>
                        {String(current.tool_result.output)}
                      </pre>
                    </>
                  )}

                  {current.tool_result?.error && (
                    <>
                      <div style={{ fontSize: 12, color: '#fca5a5', marginTop: 12 }}>Error</div>
                      <pre style={{ background: '#3f0a0a', color: '#fecaca', padding: 12, borderRadius: 6, fontSize: 13 }}>
                        {current.tool_result.error}
                      </pre>
                    </>
                  )}

                  {current.planner_output_preview && (
                    <>
                      <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 12 }}>Planner output</div>
                      <pre style={{ background: '#020617', padding: 12, borderRadius: 6, fontSize: 13, whiteSpace: 'pre-wrap' }}>
                        {current.planner_output_preview}
                      </pre>
                    </>
                  )}

                  {current.safety && (
                    <div
                      style={{
                        marginTop: 16,
                        padding: 12,
                        background: '#7f1d1d',
                        borderRadius: 6,
                      }}
                    >
                      <strong>Safety: {current.safety.risk_level}</strong> (score {current.safety.risk_score.toFixed(2)})
                      <ul style={{ marginTop: 6 }}>
                        {(current.safety.reasons ?? []).map((r, i) => <li key={i}>{r}</li>)}
                      </ul>
                    </div>
                  )}
                </>
              ) : (
                <p style={{ color: '#9ca3af' }}>No event selected.</p>
              )}
            </main>
          </div>
        </>
      )}
    </div>
  )
}

const btn: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 4,
  padding: '6px 12px',
  background: '#1e293b',
  border: '1px solid #334155',
  color: '#e5e7eb',
  borderRadius: 6,
  cursor: 'pointer',
  fontSize: 13,
}
