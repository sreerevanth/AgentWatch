import Link from 'next/link';
import { useRouter } from 'next/router';

import { Shell } from '../components/v3/Shell';
import { Empty, ErrorBox, Label, Mono, Panel, short } from '../components/v3/ui';
import { useCompare, useRuns } from '../lib/v3/client';

/** COMPARE — two runs side by side: earliest divergence, topology, information, motifs, resources. */
export default function Compare() {
  const router = useRouter();
  const runs = useRuns();
  const a = typeof router.query.a === 'string' ? router.query.a : undefined;
  const b = typeof router.query.b === 'string' ? router.query.b : undefined;
  const set = (k: 'a' | 'b', v: string) =>
    router.push({ pathname: '/compare', query: { ...router.query, [k]: v } }, undefined, {
      shallow: true,
    });
  const c = useCompare(a, b);
  const r = c.data;
  const pick = (k: 'a' | 'b', value?: string) => (
    <select
      aria-label={`run ${k}`}
      className="rounded border border-zinc-700 bg-zinc-900 px-2 py-1 font-mono text-[11px]"
      value={value ?? ''}
      onChange={(e) => set(k, e.target.value)}
    >
      <option value="">run {k.toUpperCase()}…</option>
      {runs.data?.runs.map((x) => (
        <option key={x.run_id} value={x.run_id}>
          {short(x.run_id)} · {x.name} · {x.status} · {x.started_at?.slice(11, 19)}
        </option>
      ))}
    </select>
  );
  return (
    <Shell title="COMPARE">
      <div className="mb-3 flex items-center gap-2">
        {pick('a', a)} <span className="text-zinc-500">vs</span> {pick('b', b)}
      </div>
      {!(a && b) && (
        <Empty>Pick two runs (e.g. two deployments, model versions or system versions).</Empty>
      )}
      <ErrorBox error={c.error} />
      {r && (
        <div className="grid grid-cols-12 gap-3">
          <Panel title="earliest divergence" className="col-span-12 lg:col-span-7">
            {r.earliest_divergence ? (
              <div className="space-y-2 font-mono text-[12px]">
                <div>
                  <Label tone="amber">{r.earliest_divergence.type}</Label>{' '}
                  {r.earliest_divergence.reasons.join('; ')}
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  {(['a_event', 'b_event'] as const).map((k) => {
                    const ev = r.earliest_divergence![k];
                    const run = k === 'a_event' ? a : b;
                    return (
                      <div key={k} className="rounded border border-zinc-800 p-2">
                        <div className="text-zinc-500">{k === 'a_event' ? 'A' : 'B'}</div>
                        {ev ? (
                          <Link
                            className="text-sky-400 hover:underline"
                            href={`/timeline?run=${run}&event=${ev.event_id}`}
                          >
                            {ev.label} [{short(ev.event_id)}] {ev.status}
                          </Link>
                        ) : (
                          '—'
                        )}
                      </div>
                    );
                  })}
                </div>
                {r.earliest_divergence.cone && (
                  <p className="text-[11px] text-zinc-400">
                    {r.earliest_divergence.cone.events_in_cone}/
                    {r.earliest_divergence.cone.events_total} events
                    {r.earliest_divergence.cone.latency_share !== null &&
                      ` and ${(r.earliest_divergence.cone.latency_share * 100).toFixed(0)}% of leaf latency`}{' '}
                    of B lie in the divergence point&apos;s dependency cone —{' '}
                    {r.earliest_divergence.cone.interpretation}.
                  </p>
                )}
              </div>
            ) : (
              <p className="text-sm text-zinc-400">No structural or content divergence.</p>
            )}
            <p className="mt-2 text-[10px] text-zinc-600">method: {r.method}</p>
          </Panel>
          <Panel title="versions" className="col-span-12 lg:col-span-5">
            <div className="font-mono text-[11px]">
              <div>same system version: {String(r.fingerprint.same_system_version)}</div>
              <div className="mt-1 grid grid-cols-2 gap-2 text-zinc-400">
                <pre className="whitespace-pre-wrap">
                  {JSON.stringify(r.fingerprint.a, null, 1)}
                </pre>
                <pre className="whitespace-pre-wrap">
                  {JSON.stringify(r.fingerprint.b, null, 1)}
                </pre>
              </div>
              <div className="mt-1">structural similarity {r.structural.alignment_similarity}</div>
            </div>
          </Panel>
          <Panel title="resources" className="col-span-12 lg:col-span-4">
            <table className="w-full font-mono text-[11px]">
              <thead className="text-left text-zinc-500">
                <tr>
                  <th>metric</th>
                  <th>A</th>
                  <th>B</th>
                  <th>Δ</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(r.resources).map(([k, v]) => (
                  <tr key={k} className={v.delta ? 'text-zinc-100' : 'text-zinc-500'}>
                    <td>{k}</td>
                    <td>{v.a}</td>
                    <td>{v.b}</td>
                    <td
                      className={
                        v.delta > 0 ? 'text-rose-300' : v.delta < 0 ? 'text-emerald-300' : ''
                      }
                    >
                      {v.delta}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
          <Panel title="topology differences" className="col-span-12 lg:col-span-4">
            <div className="max-h-72 overflow-auto font-mono text-[11px]">
              {r.structural.only_in_a.map((s) => (
                <div key={'a' + s.signature} className="text-rose-300">
                  − {s.signature} ×{s.count}
                </div>
              ))}
              {r.structural.only_in_b.map((s) => (
                <div key={'b' + s.signature} className="text-emerald-300">
                  + {s.signature} ×{s.count}
                </div>
              ))}
              {r.structural.edges_only_in_a.slice(0, 20).map((e, i) => (
                <div key={'ea' + i} className="text-rose-300/70">
                  − {e}
                </div>
              ))}
              {r.structural.edges_only_in_b.slice(0, 20).map((e, i) => (
                <div key={'eb' + i} className="text-emerald-300/70">
                  + {e}
                </div>
              ))}
              {r.identical_structure && <p className="text-zinc-500">identical structure</p>}
            </div>
          </Panel>
          <Panel title="information & motifs" className="col-span-12 lg:col-span-4">
            <div className="font-mono text-[11px]">
              {Object.entries(r.information).map(([k, v]) => (
                <div key={k}>
                  {k}: {v.a} → {v.b}
                </div>
              ))}
              <div className="mt-2 text-zinc-500">motifs (EXPERIMENTAL)</div>
              {Object.entries(r.motifs).map(([k, v]) => (
                <div key={k} className={v.a !== v.b ? 'text-violet-300' : 'text-zinc-500'}>
                  {k}: {v.a} → {v.b}
                </div>
              ))}
              {Object.keys(r.motifs).length === 0 && (
                <Mono className="text-zinc-500">none in either run</Mono>
              )}
            </div>
          </Panel>
        </div>
      )}
    </Shell>
  );
}
