import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/router';
import { useState } from 'react';

import { Shell } from '../components/v3/Shell';
import {
  Empty,
  ErrorBox,
  Json,
  Label,
  Maturity,
  Mono,
  Panel,
  RunLink,
  Status,
  short,
} from '../components/v3/ui';
import { post, useBranches, useRun, useStatus } from '../lib/v3/client';

/** LAB — replay, branching and counterfactual experiments. Every result states its level and provenance. */
export default function Lab() {
  const router = useRouter();
  const run = typeof router.query.run === 'string' ? router.query.run : undefined;
  const r = useRun(run);
  const status = useStatus();
  const branches = useBranches(run);
  const qc = useQueryClient();
  const reexec = Boolean(status.data?.reexecution_enabled);
  const [level, setLevel] = useState('L1');
  const [at, setAt] = useState('');
  const [value, setValue] = useState('');
  const replay = useMutation({
    mutationFn: () => post<Record<string, any>>('/replay', { run, level }),
  });
  const branch = useMutation({
    mutationFn: () =>
      post<Record<string, any>>('/branches', {
        run,
        at,
        substitute: parse(value),
        level: 'L3',
        execute: true,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['v3'] }),
  });
  const cf = useMutation({
    mutationFn: () =>
      post<Record<string, any>>('/counterfactual', {
        run,
        at,
        alternative: parse(value),
        execute: reexec,
      }),
  });
  const callable = (r.data?.events ?? []).filter((e) => typeof e.attributes.call_key === 'string');

  return (
    <Shell title="LAB" runPicker>
      {!run ? (
        <Empty>Select a run.</Empty>
      ) : (
        <div className="grid grid-cols-12 gap-3">
          <Panel
            title="replay"
            className="col-span-12 lg:col-span-6"
            right={<Maturity m="EXPERIMENTAL" />}
          >
            <p className="mb-2 text-[11px] text-zinc-500">
              L0 reconstructs the recorded timeline · L1 re-derives structure from raw evidence · L2
              re-executes with every instrumented call mocked from captures · L3 runs calls whose
              inputs changed live. Replay is never claimed deterministic: results report
              reproduction confidence and what ran live.
            </p>
            <div className="flex items-center gap-2 font-mono text-[11px]">
              {['L0', 'L1', 'L2', 'L3'].map((l) => (
                <button
                  key={l}
                  disabled={(l === 'L2' || l === 'L3') && !reexec}
                  onClick={() => setLevel(l)}
                  className={`rounded border px-2 py-0.5 disabled:opacity-40 ${level === l ? 'border-zinc-300' : 'border-zinc-700 text-zinc-500'}`}
                >
                  {l}
                </button>
              ))}
              <button
                onClick={() => replay.mutate()}
                className="ml-2 rounded bg-sky-800 px-3 py-0.5 text-sky-50"
              >
                run replay
              </button>
              {!reexec && (
                <span className="text-zinc-500">
                  L2/L3 disabled on this server (AGENTWATCH_ALLOW_REEXECUTION)
                </span>
              )}
            </div>
            <ErrorBox error={replay.error} />
            {replay.data && (
              <div className="mt-2 space-y-1 font-mono text-[11px]">
                <div>
                  <Label tone="sky">{replay.data.replay_level}</Label> {replay.data.description}
                </div>
                <div>
                  reproduction confidence {replay.data.reproduction_confidence.value} —{' '}
                  {replay.data.reproduction_confidence.basis} (uncalibrated)
                </div>
                {replay.data.replay_run && (
                  <div>
                    replay run <RunLink id={replay.data.replay_run} />
                  </div>
                )}
                <div>
                  mocked: {replay.data.mocked_components.length} · live:{' '}
                  {replay.data.live_components.join(', ') || 'none'}
                </div>
                {replay.data.missing_dependencies?.length > 0 && (
                  <div className="text-amber-300">
                    missing dependencies:{' '}
                    {JSON.stringify(replay.data.missing_dependencies).slice(0, 300)}
                  </div>
                )}
                {'consistent_with_stored_interpretation' in replay.data && (
                  <div>
                    consistent with stored interpretation:{' '}
                    {String(replay.data.consistent_with_stored_interpretation)}
                  </div>
                )}
              </div>
            )}
          </Panel>
          <Panel
            title="branch / counterfactual"
            className="col-span-12 lg:col-span-6"
            right={<Maturity m="EXPERIMENTAL" />}
          >
            <p className="mb-2 text-[11px] text-zinc-500">
              Fork the run at an instrumented call and substitute its result. Branch runs are real
              observed runs (SIMULATED). Without re-execution, counterfactuals fall back to
              MODEL_ESTIMATED (history) or UNKNOWN.
            </p>
            <select
              aria-label="branch event"
              className="mb-2 w-full rounded border border-zinc-700 bg-zinc-900 px-2 py-1 font-mono text-[11px]"
              value={at}
              onChange={(e) => setAt(e.target.value)}
            >
              <option value="">event to intervene on…</option>
              {callable.map((e) => (
                <option key={e.event_id} value={e.event_id}>
                  {short(e.event_id)} · {e.kind} {e.operation} · {String(e.attributes.call_key)}
                </option>
              ))}
            </select>
            <textarea
              aria-label="substitute value"
              className="h-24 w-full rounded border border-zinc-700 bg-zinc-900 p-2 font-mono text-[11px]"
              placeholder='substitute result as JSON, e.g. [{"id": "D5", "text": "…"}]'
              value={value}
              onChange={(e) => setValue(e.target.value)}
            />
            <div className="mt-2 flex gap-2">
              <button
                disabled={!at || !reexec}
                onClick={() => branch.mutate()}
                className="rounded bg-violet-800 px-3 py-1 font-mono text-[11px] disabled:opacity-40"
              >
                execute branch
              </button>
              <button
                disabled={!at}
                onClick={() => cf.mutate()}
                className="rounded bg-amber-800 px-3 py-1 font-mono text-[11px] disabled:opacity-40"
              >
                counterfactual
              </button>
            </div>
            <ErrorBox error={branch.error ?? cf.error} />
            {branch.data?.result && (
              <div className="mt-2 font-mono text-[11px]">
                <Label tone="violet">SIMULATED</Label> branch run{' '}
                <RunLink id={branch.data.result.branch_run} /> · outcome{' '}
                {JSON.stringify(branch.data.result.outcome)} · final outputs changed{' '}
                {String(branch.data.result.final_outputs_changed)}
              </div>
            )}
            {cf.data && (
              <div className="mt-2 space-y-1">
                <div className="font-mono text-[11px]">
                  <Label tone="amber">{cf.data.estimate?.label}</Label> {cf.data.method}
                </div>
                <Json value={cf.data.estimate} max={2000} />
              </div>
            )}
          </Panel>
          <Panel title="branch history" className="col-span-12">
            {(branches.data?.branches ?? []).length === 0 ? (
              <p className="text-xs text-zinc-500">no branches yet</p>
            ) : (
              <div className="font-mono text-[11px]">
                <div className="text-zinc-400">
                  run <RunLink id={run} /> ({r.data?.run.name})
                </div>
                {(branches.data!.branches as Record<string, any>[]).map((b) => (
                  <div key={b.branch_id} className="ml-4 border-l border-zinc-700 pl-3">
                    ├─ at {b.event_label} :={' '}
                    <Mono className="text-zinc-400">
                      {String(b.substitution_preview).slice(0, 80)}
                    </Mono>{' '}
                    → {b.result?.branch_run ? <RunLink id={b.result.branch_run} /> : 'not executed'}{' '}
                    {b.result && (
                      <>
                        outcome <Status s={b.result.outcome?.branch} /> changed=
                        {String(b.result.final_outputs_changed)} reproduction{' '}
                        {b.result.reproduction_confidence}
                      </>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>
      )}
    </Shell>
  );
}

function parse(value: string): unknown {
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}
