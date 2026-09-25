import { useState } from 'react';

import { Shell } from '../components/v3/Shell';
import { ErrorBox, Maturity, Mono, Panel } from '../components/v3/ui';
import { useDrift, useGenome, useMotifStats } from '../lib/v3/client';

/** GENOME — behaviour profiles aggregated over a scope, the motif registry, and drift between scopes. */
export default function Genome() {
  const [scope, setScope] = useState('all');
  const [draft, setDraft] = useState('all');
  const [baseline, setBaseline] = useState('');
  const [candidate, setCandidate] = useState('');
  const [driftArgs, setDriftArgs] = useState<[string, string]>(['', '']);
  const g = useGenome(scope);
  const motifs = useMotifStats();
  const drift = useDrift(driftArgs[0], driftArgs[1]);
  const d = drift.data;
  return (
    <Shell title="GENOME">
      <p className="mb-3 text-[11px] text-zinc-500">
        A genome is a descriptive fingerprint of measured structure (features v
        {String(g.data?.features_version ?? '?')}) — not a claim about model internals. Scopes:{' '}
        <code>all</code>, <code>name:&lt;run name&gt;</code>,{' '}
        <code>version:&lt;system version&gt;</code>, <code>variant:&lt;value&gt;</code>,{' '}
        <code>runs:&lt;id&gt;,&lt;id&gt;</code>.
      </p>
      <div className="grid grid-cols-12 gap-3">
        <Panel
          title="behaviour profile"
          className="col-span-12 lg:col-span-6"
          right={<Maturity m="EXPERIMENTAL" />}
        >
          <form
            className="mb-2 flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              setScope(draft);
            }}
          >
            <input
              aria-label="scope"
              className="flex-1 rounded border border-zinc-700 bg-zinc-900 px-2 py-1 font-mono text-[11px]"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
            />
            <button className="rounded bg-zinc-800 px-3 font-mono text-[11px]">apply</button>
          </form>
          <ErrorBox error={g.error} />
          {g.data && (
            <>
              <Mono className="text-zinc-400">{String(g.data.n_runs)} runs</Mono>
              <table className="mt-2 w-full font-mono text-[11px]">
                <thead className="text-left text-zinc-500">
                  <tr>
                    <th>feature</th>
                    <th>mean</th>
                    <th>95% CI (bootstrap)</th>
                    <th>range</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(
                    g.data.features as Record<
                      string,
                      { mean: number; ci95: [number, number] | null; min: number; max: number }
                    >,
                  ).map(([k, v]) => (
                    <tr key={k} className="border-t border-zinc-900">
                      <td className="py-px text-zinc-300">{k}</td>
                      <td>{v.mean.toPrecision(4)}</td>
                      <td className="text-zinc-500">
                        {v.ci95
                          ? `[${v.ci95[0].toPrecision(3)}, ${v.ci95[1].toPrecision(3)}]`
                          : 'n<2'}
                      </td>
                      <td className="text-zinc-500">
                        {v.min.toPrecision(3)} – {v.max.toPrecision(3)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="mt-2 font-mono text-[11px] text-zinc-400">
                motif frequency:{' '}
                {Object.entries(g.data.motif_frequency as Record<string, number>)
                  .map(([k, v]) => `${k}=${v}`)
                  .join('  ')}
              </div>
            </>
          )}
        </Panel>
        <Panel title="motif registry" className="col-span-12 lg:col-span-6">
          <ErrorBox error={motifs.error} />
          {(motifs.data ?? []).map((m) => (
            <details key={m.motif_id} className="border-t border-zinc-900 py-1">
              <summary className="flex cursor-pointer items-center gap-2 font-mono text-[11px]">
                <span className="text-violet-300">{m.motif_id}</span> {m.name}{' '}
                <Maturity m={m.maturity} />
                <span className="ml-auto text-zinc-500">
                  {m.instances} instances · support {Number(m.support).toFixed(2)} · error rate{' '}
                  {m.error_rate_with ?? '—'} with / {m.error_rate_without ?? '—'} without (n=
                  {m.n_with}/{m.n_without})
                </span>
              </summary>
              <p className="mt-1 text-[11px] text-zinc-400">{m.definition}</p>
            </details>
          ))}
          <p className="mt-2 text-[10px] text-zinc-600">
            Outcome associations are descriptive counts, not significance claims.
          </p>
        </Panel>
        <Panel title="drift" className="col-span-12" right={<Maturity m="EXPERIMENTAL" />}>
          <form
            className="mb-2 flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              setDriftArgs([baseline, candidate]);
            }}
          >
            <input
              aria-label="baseline scope"
              placeholder="baseline scope, e.g. version:abc"
              className="flex-1 rounded border border-zinc-700 bg-zinc-900 px-2 py-1 font-mono text-[11px]"
              value={baseline}
              onChange={(e) => setBaseline(e.target.value)}
            />
            <input
              aria-label="candidate scope"
              placeholder="candidate scope"
              className="flex-1 rounded border border-zinc-700 bg-zinc-900 px-2 py-1 font-mono text-[11px]"
              value={candidate}
              onChange={(e) => setCandidate(e.target.value)}
            />
            <button className="rounded bg-zinc-800 px-3 font-mono text-[11px]">test</button>
          </form>
          <ErrorBox error={drift.error} />
          {d && (
            <div className="font-mono text-[11px]">
              <div>
                status{' '}
                <span className={d.status === 'tested' ? 'text-sky-300' : 'text-amber-300'}>
                  {d.status}
                </span>{' '}
                · n={d.n_baseline}/{d.n_candidate} · {d.method}
                {d.min_achievable_q !== undefined && <> · min achievable q {d.min_achievable_q}</>}
              </div>
              {d.message && <div className="text-amber-300">{d.message}</div>}
              {d.behaviour_changed !== undefined && (
                <div className="mt-1">
                  behaviour changed: <b>{String(d.behaviour_changed)}</b> (
                  {(d.drifted_features ?? []).join(', ') || 'no feature below q<α'})
                </div>
              )}
              <table className="mt-2 w-full">
                <thead className="text-left text-zinc-500">
                  <tr>
                    <th>feature</th>
                    <th>baseline</th>
                    <th>candidate</th>
                    <th>relative change</th>
                    <th>q</th>
                  </tr>
                </thead>
                <tbody>
                  {(d.features as Record<string, any>[])
                    .filter((f) => f.baseline_mean !== f.candidate_mean)
                    .map((f) => (
                      <tr
                        key={f.feature}
                        className={
                          (d.drifted_features ?? []).includes(f.feature)
                            ? 'text-rose-300'
                            : 'text-zinc-400'
                        }
                      >
                        <td>{f.feature}</td>
                        <td>{f.baseline_mean}</td>
                        <td>{f.candidate_mean}</td>
                        <td>
                          {f.relative_change === null
                            ? '—'
                            : `${(f.relative_change * 100).toFixed(1)}%`}
                        </td>
                        <td>{f.q_value ?? '—'}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
              {d.distances && (
                <div className="mt-2 text-zinc-500">
                  candidate distances (none canonical):{' '}
                  {Object.entries(d.distances)
                    .filter(([k]) => k !== 'note')
                    .map(([k, v]) => `${k}=${v}`)
                    .join(' · ')}
                </div>
              )}
            </div>
          )}
        </Panel>
      </div>
    </Shell>
  );
}
