import { useState } from 'react'
import { useRouter } from 'next/router'
import useSWR from 'swr'
import { AlertTriangle, ArrowLeft, ChevronDown, ChevronUp, RotateCcw } from 'lucide-react'
import { format } from 'date-fns'

import { FailureAnalysis, ReplayStep, api } from '../../lib/api'

// Resolved at build time from the NEXT_PUBLIC_API_HOST Docker build arg.
// In production the browser calls the API origin directly (no proxy hop).
// In local dev falls back to the Next.js proxy route at /api/v1.
const API_BASE = process.env.NEXT_PUBLIC_API_HOST
  ? `https://${process.env.NEXT_PUBLIC_API_HOST}/api/v1`
  : '/api/v1'

function safeFormat(ts: string | null | undefined, fmt: string): string {
  if (!ts) return '—'
  try { return format(new Date(ts), fmt) } catch { return '—' }
}

const fetcher = async (url: string) => {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }
  return response.json()
}

const STATUS_COLORS: Record<string, string> = {
  success: '#22c55e',
  running: '#3b82f6',
  failure: '#ef4444',
  blocked: '#f59e0b',
  rolled_back: '#a855f7',
  timeout: '#f97316',
  pending: '#6b7280',
}

function statusBadge(status: string) {
  const color = STATUS_COLORS[status] ?? '#6b7280'
  return (
    <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium" style={{ backgroundColor: `${color}22`, color }}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
      {status}
    </span>
  )
}

function EventRow({ step }: { step: ReplayStep }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="rounded-xl border border-white/10 bg-black/10">
      <button type="button" className="flex w-full items-center gap-3 px-4 py-3 text-left text-sm" onClick={() => setExpanded((value) => !value)}>
        <span className="w-12 font-mono text-xs text-zinc-500">{String(step.index).padStart(4, '0')}</span>
        <span className="min-w-0 flex-1 truncate text-zinc-200">{step.event.event_type}</span>
        <span className="font-mono text-xs text-zinc-500">{step.event.tool_call?.tool_name ?? '—'}</span>
        <span>{statusBadge(step.event.status)}</span>
        <span className="text-xs text-zinc-500">{safeFormat(step.event.timestamp, 'HH:mm:ss.SSS')}</span>
        {expanded ? <ChevronUp size={14} className="text-zinc-500" /> : <ChevronDown size={14} className="text-zinc-500" />}
      </button>
      {expanded ? (
        <div className="space-y-2 border-t border-white/10 px-4 py-3 text-xs text-zinc-400">
          {step.event.tool_call?.raw_command ? <div><span className="text-zinc-500">Command:</span> <code>{step.event.tool_call.raw_command}</code></div> : null}
          {step.event.tool_result?.output ? <div><span className="text-zinc-500">Output:</span> {String(step.event.tool_result.output).slice(0, 300)}</div> : null}
          {step.event.tool_result?.error ? <div className="text-red-300">{step.event.tool_result.error}</div> : null}
          {step.annotations.length > 0 ? <div><span className="text-zinc-500">Annotations:</span> {step.annotations.join(', ')}</div> : null}
        </div>
      ) : null}
    </div>
  )
}

function FailurePanel({ analysis }: { analysis: FailureAnalysis }) {
  return (
    <section className="rounded-2xl border border-red-500/20 bg-red-500/5 p-5">
      <div className="mb-3 flex items-center gap-2 text-red-300">
        <AlertTriangle size={16} />
        <h2 className="text-sm font-semibold uppercase tracking-[0.2em]">Failure Analysis</h2>
      </div>
      <div className="text-sm text-zinc-300">{analysis.summary}</div>
      <div className="mt-3 text-xs text-zinc-500">Primary cause: {analysis.primary_cause}</div>
      {analysis.recommendations.length > 0 ? (
        <div className="mt-4 space-y-1 text-sm text-zinc-300">
          {analysis.recommendations.map((recommendation) => <div key={recommendation}>→ {recommendation}</div>)}
        </div>
      ) : null}
    </section>
  )
}

export default function SessionPage() {
  const router = useRouter()
  const { id } = router.query as { id?: string }
  const [rollbackStep, setRollbackStep] = useState('')
  const { data: session } = useSWR(id ? `${API_BASE}/sessions/${id}` : null, fetcher)
  const { data: replayData } = useSWR(id ? `${API_BASE}/sessions/${id}/replay` : null, fetcher)
  const { data: confidenceData } = useSWR(id ? `${API_BASE}/sessions/${id}/confidence` : null, fetcher)
  const { data: checkpointsData } = useSWR(id ? `${API_BASE}/sessions/${id}/checkpoints` : null, fetcher)

  if (!id) return null

  const handleRollback = async () => {
    if (!rollbackStep) return
    await api.rollback(id, { to_step: Number(rollbackStep) })
    window.alert(`Rollback to step ${rollbackStep} triggered.`)
  }

  return (
    <div className="min-h-screen bg-agentwatch text-white">
      <header className="border-b border-white/10 bg-zinc-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-screen-2xl items-center gap-4 px-6 py-4">
          <button type="button" onClick={() => router.push('/')} className="inline-flex items-center gap-2 text-sm text-zinc-400 transition hover:text-white">
            <ArrowLeft size={14} />
            Dashboard
          </button>
          <div className="font-mono text-sm text-zinc-300">{id}</div>
          {session ? statusBadge(session.status) : null}
        </div>
      </header>

      <main className="mx-auto max-w-screen-2xl space-y-6 px-6 py-6">
        {session ? (
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4"><div className="text-xs uppercase tracking-[0.2em] text-zinc-500">Framework</div><div className="mt-3 text-xl text-white">{session.framework}</div></div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4"><div className="text-xs uppercase tracking-[0.2em] text-zinc-500">Events</div><div className="mt-3 text-xl text-white">{session.total_events}</div></div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4"><div className="text-xs uppercase tracking-[0.2em] text-zinc-500">Tokens</div><div className="mt-3 text-xl text-white">{session.total_tokens.toLocaleString()}</div></div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4"><div className="text-xs uppercase tracking-[0.2em] text-zinc-500">Cost</div><div className="mt-3 text-xl text-white">${session.estimated_cost_usd.toFixed(4)}</div></div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4"><div className="text-xs uppercase tracking-[0.2em] text-zinc-500">Confidence</div><div className="mt-3 text-xl text-white">{confidenceData ? `${Math.round(confidenceData.overall_score * 100)}%` : '—'}</div></div>
          </section>
        ) : null}

        {session?.goal ? <section className="rounded-2xl border border-white/10 bg-white/5 p-5 text-zinc-300">{session.goal}</section> : null}
        {replayData?.failure_analysis ? <FailurePanel analysis={replayData.failure_analysis} /> : null}

        <section className="rounded-2xl border border-white/10 bg-white/5">
          <div className="border-b border-white/10 px-5 py-4">
            <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-zinc-300">Execution Trace</h2>
          </div>
          <div className="space-y-2 p-3">
            {(replayData?.steps ?? []).map((step: ReplayStep) => <EventRow key={step.index} step={step} />)}
          </div>
        </section>

        {(checkpointsData?.checkpoints ?? []).length > 0 ? (
          <section className="rounded-2xl border border-white/10 bg-white/5 p-5">
            <div className="mb-4 flex items-center gap-2 text-violet-300">
              <RotateCcw size={16} />
              <h2 className="text-sm font-semibold uppercase tracking-[0.2em]">Rollback</h2>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <select value={rollbackStep} onChange={(event) => setRollbackStep(event.target.value)} className="rounded-xl border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-white">
                <option value="">Select checkpoint</option>
                {checkpointsData.checkpoints.map((checkpoint: { checkpoint_id: string; step_number: number; checkpoint_type: string }) => (
                  <option key={checkpoint.checkpoint_id} value={checkpoint.step_number}>
                    Step {checkpoint.step_number} — {checkpoint.checkpoint_type}
                  </option>
                ))}
              </select>
              <button type="button" disabled={!rollbackStep} onClick={handleRollback} className="rounded-xl bg-violet-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-violet-500 disabled:opacity-50">
                Trigger rollback
              </button>
            </div>
          </section>
        ) : null}
      </main>
    </div>
  )
}
