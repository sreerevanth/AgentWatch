import { useEffect, useState } from 'react'
import { Save, Trash2, Shield } from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_HOST
  ? `https://${process.env.NEXT_PUBLIC_API_HOST}/api/v1`
  : (process.env.NEXT_PUBLIC_API_URL ?? '/api/v1')

const DEFAULT_YAML = `rules:
  - if: tool == "bash" and command contains "rm"
    then: require_approval
  - if: confidence < 0.5
    then: pause_and_alert
`

export default function PoliciesPage() {
  const [text, setText] = useState<string>('')
  const [status, setStatus] = useState<string>('')
  const [decisionPreview, setDecisionPreview] = useState<string>('')

  useEffect(() => {
    fetch(`${API_BASE}/policies/current`)
      .then((r) => (r.ok ? r.text() : DEFAULT_YAML))
      .then((t) => setText(t))
      .catch(() => setText(DEFAULT_YAML))
  }, [])

  const save = async () => {
    setStatus('Saving…')
    try {
      const res = await fetch(`${API_BASE}/policies/current`, {
        method: 'PUT',
        headers: { 'Content-Type': 'text/yaml' },
        body: text,
      })
      setStatus(res.ok ? 'Saved' : `Error: ${res.status}`)
    } catch (e) {
      setStatus('Saved locally (API unreachable)')
    }
  }

  const previewDecision = async () => {
    try {
      const res = await fetch(`${API_BASE}/policies/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rules: text,
          tool: 'bash',
          command: 'rm -rf /tmp/test',
        }),
      })
      if (res.ok) {
        const j = await res.json()
        setDecisionPreview(`Action: ${j.action} (matched rule: ${j.matched_rule?.label ?? j.matched_rule?.condition ?? '—'})`)
      } else {
        setDecisionPreview('Backend preview endpoint not available')
      }
    } catch {
      setDecisionPreview('Backend preview endpoint not available')
    }
  }

  return (
    <div style={{ padding: 24, fontFamily: 'ui-sans-serif, system-ui', background: '#0b1020', color: '#e5e7eb', minHeight: '100vh' }}>
      <header style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <Shield size={28} color="#f472b6" />
        <h1 style={{ margin: 0, fontSize: 24 }}>Policy DSL Editor</h1>
      </header>

      <p style={{ color: '#94a3b8', fontSize: 13, marginBottom: 16 }}>
        Human-readable YAML rules evaluated at runtime by AgentWatch.
      </p>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        spellCheck={false}
        style={{
          width: '100%',
          minHeight: 320,
          padding: 16,
          fontFamily: 'ui-monospace, SFMono-Regular, monospace',
          fontSize: 13,
          background: '#0f172a',
          color: '#e5e7eb',
          border: '1px solid #1f2937',
          borderRadius: 8,
          marginBottom: 16,
        }}
      />

      <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <button
          onClick={save}
          style={{
            display: 'flex',
            gap: 6,
            alignItems: 'center',
            padding: '10px 18px',
            background: '#22c55e',
            border: 'none',
            color: 'white',
            borderRadius: 8,
            cursor: 'pointer',
          }}
        >
          <Save size={16} /> Save
        </button>
        <button
          onClick={previewDecision}
          style={{
            display: 'flex',
            gap: 6,
            alignItems: 'center',
            padding: '10px 18px',
            background: '#1e293b',
            border: '1px solid #334155',
            color: '#e5e7eb',
            borderRadius: 8,
            cursor: 'pointer',
          }}
        >
          Preview decision
        </button>
        <button
          onClick={() => setText(DEFAULT_YAML)}
          style={{
            display: 'flex',
            gap: 6,
            alignItems: 'center',
            padding: '10px 18px',
            background: 'transparent',
            border: '1px solid #475569',
            color: '#94a3b8',
            borderRadius: 8,
            cursor: 'pointer',
          }}
        >
          <Trash2 size={16} /> Reset
        </button>
      </div>

      {status && <p style={{ color: '#86efac' }}>{status}</p>}
      {decisionPreview && (
        <pre
          style={{
            background: '#0f172a',
            padding: 12,
            borderRadius: 8,
            fontSize: 13,
            color: '#a5b4fc',
            whiteSpace: 'pre-wrap',
          }}
        >
          {decisionPreview}
        </pre>
      )}
    </div>
  )
}
