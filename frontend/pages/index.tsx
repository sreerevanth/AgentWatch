import type { ComponentType } from 'react'
import { useState } from 'react'
import { useRouter } from 'next/router'
import useSWR from 'swr'
import { Activity, AlertTriangle, ChevronRight, DollarSign, Loader2, RefreshCw, Shield, Zap } from 'lucide-react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { format, formatDistanceToNow } from 'date-fns'

import { AgentEvent, AgentSession, DashboardSummary } from '../lib/api'
import { useLiveEventSocket } from '../lib/useLiveEventSocket'
import type { LiveFeedStatus } from '../lib/wsReconnect'

// Resolved at build time from the NEXT_PUBLIC_API_HOST Docker build arg.
// In production the browser calls the API origin directly (no proxy hop).
// In local dev falls back to the Next.js proxy route at /api/v1.
const API_BASE = process.env.NEXT_PUBLIC_API_HOST
  ? `https://${process.env.NEXT_PUBLIC_API_HOST}/api/v1`
  : '/api/v1'

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

function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ')
}

function safeFormat(ts: string | null | undefined, fmt: string): string {
  if (!ts) return '—'
  try { return format(new Date(ts), fmt) } catch { return '—' }
}

function safeDistanceToNow(ts: string | null | undefined): string {
  if (!ts) return '—'
  try { return formatDistanceToNow(new Date(ts), { addSuffix: true }) } catch { return '—' }
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

function MetricCard({
  icon: Icon,
  label,
  value,
  sub,
  color,
  loading,
}: {
  icon: ComponentType<{ size?: string | number }>
  label: string
  value: string | number
  sub?: string
  color: string
  loading?: boolean
}) {
  if (loading) {
    return (
      <div className="rounded-2xl border border-white/10 bg-white/5 p-5 shadow-[0_20px_80px_rgba(0,0,0,0.22)]">
        <div className="flex items-center justify-between">
          <div className="flex-1 animate-pulse">
            <div className="h-3 w-24 rounded bg-white/10" />
            <div className="mt-4 h-8 w-20 rounded bg-white/10" />
            <div className="mt-2 h-3 w-32 rounded bg-white/10" />
          </div>
          <div className="h-11 w-11 rounded-xl bg-white/10" />
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-5 shadow-[0_20px_80px_rgba(0,0,0,0.22)]">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs uppercase tracking-[0.24em] text-zinc-500">{label}</div>
          <div className="mt-3 text-3xl font-semibold text-white">{value}</div>
          {sub ? <div className="mt-1 text-xs text-zinc-400">{sub}</div> : null}
        </div>
        <div className="rounded-xl p-3" style={{ backgroundColor: `${color}22`, color }}>
          <Icon size={18} />
        </div>
      </div>
    </div>
  )
}

function liveFeedBadge(status: LiveFeedStatus, reconnectElapsedSec: number) {
  if (status === 'streaming') {
    return (
      <span className="inline-flex items-center gap-2 text-xs text-emerald-400">
        <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
        streaming
      </span>
    )
  }
  if (status === 'reconnecting') {
    return (
      <span className="inline-flex items-center gap-2 text-xs text-amber-300">
        <Loader2 className="h-3 w-3 animate-spin" />
        Reconnecting… {reconnectElapsedSec}s
      </span>
    )
  }
  if (status === 'failed') {
    return (
      <span className="inline-flex items-center gap-2 text-xs text-red-400">
        Connection failed — refresh to retry
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-2 text-xs text-zinc-500">
      <Loader2 className="h-3 w-3 animate-spin" />
      connecting
    </span>
  )
}

function LiveEventFeed({
  events,
  wsStatus,
  reconnectElapsedSec,
}: {
  events: AgentEvent[]
  wsStatus: LiveFeedStatus
  reconnectElapsedSec: number
}) {
  return (
    <section className="rounded-2xl border border-white/10 bg-white/5 p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-zinc-300">Live Feed</h2>
        {liveFeedBadge(wsStatus, reconnectElapsedSec)}
      </div>
      <div className="max-h-[24rem] space-y-2 overflow-y-auto pr-1">
        {wsStatus === 'connecting' ? (
          <div className="space-y-2">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="animate-pulse rounded-xl border border-white/5 bg-white/5 p-3 text-xs">
                <div className="flex items-center justify-between gap-3">
                  <div className="h-3 w-24 rounded bg-white/10" />
                  <div className="h-3 w-12 rounded bg-white/10" />
                </div>
                <div className="mt-2 h-3 w-40/50 rounded bg-white/10" style={{ width: '60%' }} />
              </div>
            ))}
          </div>
        ) : events.length === 0 ? (
          <div className="py-10 text-center text-sm text-zinc-500">Waiting for events…</div>
        ) : null}
        {events.slice(0, 40).map((event) => (
          <div key={event.event_id} className={cn('rounded-xl border px-3 py-2 text-xs', event.safety?.blocked ? 'border-red-500/30 bg-red-500/10' : 'border-white/5 bg-black/10')}>
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="truncate font-medium text-zinc-200">{event.event_type}</div>
                <div className="truncate font-mono text-zinc-500">{event.tool_call?.raw_command ?? event.tool_call?.tool_name ?? event.agent_id}</div>
              </div>
              <div className="shrink-0 text-zinc-500">{safeFormat(event.timestamp, 'HH:mm:ss')}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

function SessionsTable({ sessions, loading }: { sessions: AgentSession[]; loading?: boolean }) {
  const router = useRouter()
  return (
    <section className="rounded-2xl border border-white/10 bg-white/5">
      <div className="border-b border-white/10 px-5 py-4">
        <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-zinc-300">Recent Sessions</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase tracking-[0.16em] text-zinc-500">
            <tr>
              <th className="px-5 py-3">Session</th>
              <th className="px-4 py-3">Framework</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Events</th>
              <th className="px-4 py-3 text-right">Tokens</th>
              <th className="px-4 py-3 text-right">Cost</th>
              <th className="px-4 py-3 text-right">Started</th>
              <th className="px-5 py-3" />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              [...Array(5)].map((_, i) => (
                <tr key={i} className="animate-pulse border-t border-white/5">
                  <td className="px-5 py-3">
                    <div className="mb-2 h-3 w-32 rounded bg-white/10" />
                    <div className="h-3 w-48 rounded bg-white/10" />
                  </td>
                  <td className="px-4 py-3"><div className="h-3 w-16 rounded bg-white/10" /></td>
                  <td className="px-4 py-3"><div className="h-5 w-20 rounded-full bg-white/10" /></td>
                  <td className="px-4 py-3"><div className="ml-auto h-3 w-8 rounded bg-white/10" /></td>
                  <td className="px-4 py-3"><div className="ml-auto h-3 w-12 rounded bg-white/10" /></td>
                  <td className="px-4 py-3"><div className="ml-auto h-3 w-12 rounded bg-white/10" /></td>
                  <td className="px-4 py-3"><div className="ml-auto h-3 w-20 rounded bg-white/10" /></td>
                  <td className="px-5 py-3" />
                </tr>
              ))
            ) : (
              sessions.map((session) => (
                <tr key={session.session_id} className="cursor-pointer border-t border-white/5 transition-colors hover:bg-white/5" onClick={() => router.push(`/sessions/${session.session_id}`)}>
                  <td className="px-5 py-3">
                    <div className="font-mono text-xs text-zinc-200">{session.session_id.slice(0, 16)}…</div>
                    <div className="max-w-[20rem] truncate text-xs text-zinc-500">{session.goal ?? session.agent_name ?? session.agent_id}</div>
                  </td>
                  <td className="px-4 py-3 text-zinc-300">{session.framework}</td>
                  <td className="px-4 py-3">{statusBadge(session.status)}</td>
                  <td className="px-4 py-3 text-right font-mono text-zinc-300">{session.total_events}</td>
                  <td className="px-4 py-3 text-right font-mono text-zinc-300">{session.total_tokens.toLocaleString()}</td>
                  <td className="px-4 py-3 text-right font-mono text-zinc-300">${session.estimated_cost_usd.toFixed(4)}</td>
                  <td className="px-4 py-3 text-right text-xs text-zinc-500">{safeDistanceToNow(session.started_at)}</td>
                  <td className="px-5 py-3 text-zinc-500"><ChevronRight size={14} /></td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function SafetyPanel({ blockedEvents, loading }: { blockedEvents: AgentEvent[]; loading?: boolean }) {
  return (
    <section className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-amber-300">Safety Blocks</h2>
        <span className="rounded-full bg-amber-500/20 px-2 py-1 text-xs font-medium text-amber-300">{loading ? '…' : blockedEvents.length}</span>
      </div>
      <div className="space-y-2">
        {loading ? (
          [...Array(3)].map((_, i) => (
            <div key={i} className="animate-pulse rounded-xl border border-amber-500/10 bg-black/10 p-3 text-xs">
              <div className="flex items-center justify-between gap-3">
                <div className="h-3 w-24 rounded bg-white/10" />
                <div className="h-3 w-12 rounded bg-white/10" />
              </div>
              <div className="mt-2 h-3 w-40 rounded bg-white/10" />
              <div className="mt-3 h-3 w-32 rounded bg-amber-500/20" />
            </div>
          ))
        ) : blockedEvents.length === 0 ? (
          <div className="text-sm text-zinc-500">No blocked actions in the current window.</div>
        ) : (
          blockedEvents.slice(0, 6).map((event) => (
            <div key={event.event_id} className="rounded-xl border border-amber-500/10 bg-black/10 p-3 text-xs">
              <div className="flex items-center justify-between gap-3">
                <div className="font-medium text-zinc-200">{event.tool_call?.tool_name ?? event.event_type}</div>
                <div className="text-zinc-500">{safeFormat(event.timestamp, 'HH:mm:ss')}</div>
              </div>
              <div className="mt-1 truncate font-mono text-zinc-500">{event.tool_call?.raw_command}</div>
              <div className="mt-2 text-amber-300">{event.safety?.reasons?.[0] ?? 'Blocked by policy'}</div>
            </div>
          ))
        )}
      </div>
    </section>
  )
}

export default function DashboardPage() {
  const { data: summary, mutate: refreshSummary, isLoading: summaryLoading } = useSWR<DashboardSummary>(`${API_BASE}/dashboard/summary`, fetcher, { refreshInterval: 15000 })
  const { data: sessionsData, mutate: refreshSessions, isLoading: sessionsLoading } = useSWR<{ sessions: AgentSession[]; total: number }>(`${API_BASE}/sessions?limit=20`, fetcher, { refreshInterval: 15000 })
  const { data: blockedData, isLoading: blockedLoading } = useSWR<{ blocked_events: AgentEvent[]; total: number }>(`${API_BASE}/safety/blocked?limit=20`, fetcher, { refreshInterval: 15000 })
  const [liveEvents, setLiveEvents] = useState<AgentEvent[]>([])
  const { status: wsStatus, reconnectElapsedSec } = useLiveEventSocket(
    (event) => {
      setLiveEvents((previous) => [event, ...previous].slice(0, 200))
    },
    () => {
      refreshSummary()
      refreshSessions()
    },
  )

  const sessions = sessionsData?.sessions ?? []
  const blockedEvents = blockedData?.blocked_events ?? []
  const confidenceTrend = sessions
    .slice(0, 12)
    .reverse()
    .map((session, index) => ({
      index,
      confidence: Math.round((session.final_confidence ?? 0) * 100),
    }))

  return (
    <div className="min-h-screen bg-agentwatch text-white">
      <header className="sticky top-0 z-40 border-b border-white/10 bg-zinc-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-screen-2xl items-center justify-between px-6 py-4">
          <div>
            <div className="text-xs uppercase tracking-[0.32em] text-zinc-500">AgentWatch</div>
            <h1 className="text-2xl font-semibold text-white">Reliability, safety, and observability</h1>
          </div>
          <button onClick={() => { refreshSummary(); refreshSessions() }} className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-zinc-300 transition hover:bg-white/10 hover:text-white">
            <RefreshCw size={14} />
            Refresh
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-screen-2xl space-y-6 px-6 py-6">
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard icon={Activity} label="Total Sessions" value={summary?.total_sessions ?? '—'} sub={`${summary?.active_sessions ?? 0} active`} color="#3b82f6" loading={summaryLoading} />
          <MetricCard icon={AlertTriangle} label="Failed Sessions" value={summary?.failed_sessions ?? '—'} sub={`${summary?.blocked_sessions ?? 0} blocked`} color="#ef4444" loading={summaryLoading} />
          <MetricCard icon={Shield} label="Safety Checks" value={summary?.safety_stats?.checked ?? '—'} sub={`${summary?.safety_stats?.blocked ?? 0} blocked`} color="#f59e0b" loading={summaryLoading} />
          <MetricCard icon={DollarSign} label="Estimated Cost" value={`$${(summary?.estimated_cost_usd ?? 0).toFixed(4)}`} sub={`${(summary?.total_tokens ?? 0).toLocaleString()} tokens`} color="#22c55e" loading={summaryLoading} />
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.05fr_1.95fr]">
          <LiveEventFeed events={liveEvents} wsStatus={wsStatus} reconnectElapsedSec={reconnectElapsedSec} />
          <SessionsTable sessions={sessions} loading={sessionsLoading} />
        </section>

        <section className="grid gap-6 lg:grid-cols-[1fr_1.6fr]">
          <SafetyPanel blockedEvents={blockedEvents} loading={blockedLoading} />
          <section className="rounded-2xl border border-white/10 bg-white/5 p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-zinc-300">Confidence Trend</h2>
              <div className="inline-flex items-center gap-2 text-xs text-blue-300">
                <Zap size={12} />
                recent sessions
              </div>
            </div>
            {sessionsLoading ? (
              <div className="flex h-48 animate-pulse items-center justify-center rounded-xl bg-white/5">
                <div className="flex h-32 w-full flex-col justify-end px-4">
                  <div className="flex items-end gap-2 h-full">
                    {[...Array(12)].map((_, i) => (
                      <div key={i} className="flex-1 bg-white/10 rounded-t" style={{ height: `${Math.random() * 60 + 20}%` }} />
                    ))}
                  </div>
                </div>
              </div>
            ) : confidenceTrend.length === 0 ? (
              <div className="flex h-48 items-center justify-center text-sm text-zinc-500">Run a session to populate the dashboard.</div>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={confidenceTrend}>
                  <defs>
                    <linearGradient id="confidenceFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.38} />
                      <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="#ffffff08" strokeDasharray="4 4" />
                  <XAxis dataKey="index" hide />
                  <YAxis domain={[0, 100]} tick={{ fill: '#71717a', fontSize: 12 }} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ background: '#18181b', border: '1px solid #27272a', borderRadius: 16 }} />
                  <Area dataKey="confidence" type="monotone" stroke="#60a5fa" fill="url(#confidenceFill)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </section>
        </section>
      </main>
    </div>
  )
}
