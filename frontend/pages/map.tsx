import { useRouter } from 'next/router';
import { useMemo, useState } from 'react';

import { EventInspector } from '../components/v3/EventInspector';
import { GraphView } from '../components/v3/GraphView';
import { Shell } from '../components/v3/Shell';
import { Empty, ErrorBox, Label, Mono, Panel } from '../components/v3/ui';
import { useGraph, useProvenance } from '../lib/v3/client';
import { cone, edgesOf, EVIDENCE_COLOR, VIEW_COLOR } from '../lib/v3/graph';

type Focus = 'none' | 'ancestors' | 'descendants' | 'cone' | 'provenance';

/** MAP — computational topology of a run, switchable between execution, information and causal views. */
export default function MapView() {
  const router = useRouter();
  const run = typeof router.query.run === 'string' ? router.query.run : undefined;
  const [view, setView] = useState<'execution' | 'information' | 'causal' | 'all'>('execution');
  const [kinds, setKinds] = useState({
    event: true,
    artifact: view !== 'execution',
    entity: false,
  });
  const [selected, setSelected] = useState<string | null>(null);
  const [focus, setFocus] = useState<Focus>('none');
  const g = useGraph(run, view);
  const prov = useProvenance(focus === 'provenance' ? selected : null, run);

  const nodes = useMemo(() => (g.data?.nodes ?? []).filter((n) => kinds[n.type]), [g.data, kinds]);
  const visible = useMemo(() => new Set(nodes.map((n) => n.node)), [nodes]);
  const relations = useMemo(
    () =>
      (g.data?.relations ?? []).filter(
        (r) => r.tail.some((t) => visible.has(t)) && r.head.some((h) => visible.has(h)),
      ),
    [g.data, visible],
  );
  const edges = useMemo(() => edgesOf(relations), [relations]);
  const highlight = useMemo(() => {
    if (!selected || focus === 'none') return null;
    if (focus === 'provenance') {
      const s = new Set<string>([selected]);
      const walk = (n: { node: string; parents: unknown[] }) => {
        s.add(n.node);
        (n.parents as { node: string; parents: unknown[] }[]).forEach(walk);
      };
      if (prov.data?.root) walk(prov.data.root);
      return s;
    }
    const up =
      focus === 'ancestors' || focus === 'cone' ? cone(selected, edges, 'up') : new Set<string>();
    const down =
      focus === 'descendants' || focus === 'cone'
        ? cone(selected, edges, 'down')
        : new Set<string>();
    return new Set([...up, ...down, selected]);
  }, [selected, focus, edges, prov.data]);

  const selectedEvent = selected?.startsWith('event:') ? selected.slice(6) : null;
  return (
    <Shell title="MAP" runPicker>
      {!run ? (
        <Empty>Select a run.</Empty>
      ) : (
        <div className="grid grid-cols-12 gap-3">
          <div className="col-span-12 space-y-2 xl:col-span-8">
            <div className="flex flex-wrap items-center gap-2 font-mono text-[11px]">
              {(['execution', 'information', 'causal', 'all'] as const).map((v) => (
                <button
                  key={v}
                  onClick={() => {
                    setView(v);
                    setKinds({ event: true, artifact: v !== 'execution', entity: false });
                  }}
                  className={`rounded border px-2 py-0.5 ${view === v ? 'border-zinc-400 text-zinc-100' : 'border-zinc-700 text-zinc-500'}`}
                >
                  {v}
                </button>
              ))}
              <span className="mx-2 text-zinc-600">|</span>
              {(['event', 'artifact', 'entity'] as const).map((k) => (
                <label key={k} className="flex items-center gap-1 text-zinc-400">
                  <input
                    type="checkbox"
                    checked={kinds[k]}
                    onChange={(e) => setKinds({ ...kinds, [k]: e.target.checked })}
                  />{' '}
                  {k}s
                </label>
              ))}
              <span className="mx-2 text-zinc-600">|</span>
              {(['none', 'ancestors', 'descendants', 'cone', 'provenance'] as const).map((f) => (
                <button
                  key={f}
                  disabled={!selected}
                  onClick={() => setFocus(f)}
                  className={`rounded px-2 py-0.5 ${focus === f ? 'bg-zinc-800 text-zinc-100' : 'text-zinc-500'} disabled:opacity-40`}
                >
                  {f === 'cone'
                    ? 'causal cone'
                    : f === 'provenance'
                      ? 'provenance path'
                      : f === 'none'
                        ? 'no focus'
                        : `expand ${f}`}
                </button>
              ))}
            </div>
            <ErrorBox error={g.error} />
            {view === 'causal' && relations.length === 0 && (
              <Panel>
                <p className="text-sm text-zinc-400">
                  No causal relations. The causal view only contains hypotheses backed by recorded
                  evidence (interventions from LAB branches, or explicitly added evidence).
                  Structural dependency is shown in the execution and information views and is never
                  labelled causal.
                </p>
              </Panel>
            )}
            {nodes.length > 0 && (
              <GraphView
                nodes={nodes}
                relations={relations}
                selected={selected}
                highlight={highlight}
                onSelect={setSelected}
              />
            )}
            <div className="flex flex-wrap gap-3 font-mono text-[10px] text-zinc-500">
              {Object.entries(VIEW_COLOR).map(([k, c]) => (
                <span key={k}>
                  <span style={{ color: c }}>━</span> {k.toLowerCase()}
                </span>
              ))}
              <span>╌ inferred (non-declared) · opacity = confidence</span>
              {Object.entries(EVIDENCE_COLOR).map(([k, c]) => (
                <span key={k}>
                  <span style={{ color: c }}>━</span> {k.toLowerCase()}
                </span>
              ))}
            </div>
          </div>
          <div className="col-span-12 space-y-3 xl:col-span-4">
            <Panel title="graph">
              <Mono className="text-zinc-400">
                {nodes.length} nodes · {relations.length} relations
              </Mono>
              {g.data?.stats && (
                <div className="mt-1 font-mono text-[11px] text-zinc-500">
                  depth {String(g.data.stats.max_depth)} · branching{' '}
                  {String(g.data.stats.mean_branching)} · multi-parent{' '}
                  {String(g.data.stats.multi_parent_events)}
                </div>
              )}
              {selected && (
                <div className="mt-2 font-mono text-[11px]">
                  <Label>selected</Label> {selected}
                </div>
              )}
            </Panel>
            {selectedEvent ? (
              <EventInspector
                eventId={selectedEvent}
                runId={run}
                onSelect={(id) => setSelected(`event:${id}`)}
              />
            ) : (
              selected && (
                <Panel title="node">
                  <Mono>{g.data?.nodes.find((n) => n.node === selected)?.label}</Mono>
                  <p className="mt-1 break-all text-[11px] text-zinc-500">
                    {g.data?.nodes.find((n) => n.node === selected)?.preview}
                  </p>
                </Panel>
              )
            )}
          </div>
        </div>
      )}
    </Shell>
  );
}
