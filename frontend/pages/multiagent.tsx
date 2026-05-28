import useSWR from 'swr'
import { Users, GitBranch, AlertCircle } from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_HOST
  ? `https://${process.env.NEXT_PUBLIC_API_HOST}/api/v1`
  : (process.env.NEXT_PUBLIC_API_URL ?? '/api/v1')

const fetcher = (url: string) => fetch(url).then((r) => (r.ok ? r.json() : null))

interface DagNode {
  node_id: string
  agent_id: string
  action: string
  timestamp: string
}
interface DagEdge {
  src: string
  dst: string
  kind: string
}
interface DagPayload {
  nodes: DagNode[]
  edges: DagEdge[]
}

interface DeadlockReport {
  deadlocked: boolean
  cycle: string[]
  detail: string
}

export default function MultiAgentPage() {
  const { data: dag } = useSWR<DagPayload>(`${API_BASE}/orchestration/dag`, fetcher, { refreshInterval: 5_000 })
  const { data: deadlock } = useSWR<DeadlockReport>(`${API_BASE}/orchestration/deadlock`, fetcher, { refreshInterval: 5_000 })

  const nodes = dag?.nodes ?? []
  const edges = dag?.edges ?? []
  const agents = new Set(nodes.map((n) => n.agent_id))

  return (
    <div style={{ padding: 24, fontFamily: 'ui-sans-serif, system-ui', background: '#0b1020', color: '#e5e7eb', minHeight: '100vh' }}>
      <header style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <Users size={28} color="#22d3ee" />
        <h1 style={{ margin: 0, fontSize: 24 }}>Multi-Agent Map</h1>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16, marginBottom: 24 }}>
        <Stat label="Distinct agents" value={agents.size} icon={<Users size={18} />} />
        <Stat label="Conversation nodes" value={nodes.length} icon={<GitBranch size={18} />} />
        <Stat label="Inter-agent edges" value={edges.length} icon={<GitBranch size={18} />} />
      </div>

      {deadlock?.deadlocked && (
        <div style={{ padding: 14, borderRadius: 10, background: '#7f1d1d', marginBottom: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <AlertCircle size={18} />
            <strong>Deadlock detected</strong>
          </div>
          <p style={{ marginTop: 6, fontSize: 13, opacity: 0.9 }}>{deadlock.detail}</p>
          <code style={{ fontSize: 12 }}>{deadlock.cycle.join(' → ')}</code>
        </div>
      )}

      <section>
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>Agent activity</h2>
        {nodes.length === 0 ? (
          <p style={{ color: '#9ca3af' }}>No multi-agent activity yet. Run a crew to populate the graph.</p>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 10 }}>
            {nodes.slice(-50).reverse().map((n) => (
              <div key={n.node_id} style={{ padding: 12, background: '#0f172a', borderRadius: 8 }}>
                <div style={{ fontSize: 11, color: '#94a3b8', textTransform: 'uppercase' }}>{n.agent_id}</div>
                <div style={{ fontWeight: 600, marginTop: 4 }}>{n.action}</div>
                <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>{new Date(n.timestamp).toLocaleString()}</div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

function Stat({ label, value, icon }: { label: string; value: number; icon: React.ReactNode }) {
  return (
    <div style={{ padding: 16, background: '#0f172a', borderRadius: 10, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <div>
        <div style={{ fontSize: 12, color: '#9ca3af' }}>{label}</div>
        <div style={{ fontSize: 28, fontWeight: 700, marginTop: 4 }}>{value}</div>
      </div>
      {icon}
    </div>
  )
}
