import { useRouter } from 'next/router';
import { useMemo, useState } from 'react';

import { EventInspector } from '../components/v3/EventInspector';
import { GraphView } from '../components/v3/GraphView';
import { Shell } from '../components/v3/Shell';
import { Empty, ErrorBox, Label, Mono, Panel } from '../components/v3/ui';
import { useGraph, useProvenance, useProvenanceEvidence } from '../lib/v3/client';
import { cone, edgesOf, EVIDENCE_COLOR, isNonFlow, VIEW_COLOR } from '../lib/v3/graph';

type Focus = 'none' | 'ancestors' | 'descendants' | 'cone' | 'provenance';

/** MAP — computational topology of a run, switchable between execution, information and causal views. */
export default function MapView() {
  const router = useRouter();
  const run = typeof router.query.run === 'string' ? router.query.run : undefined;
  const [view, setView] = useState<'execution' | 'information' | 'causal' | 'all'>('execution');
  const [kinds, setKinds] = useState({
    event: true,
    instance: view !== 'execution',
    entity: false,
  });
  const [showCandidates, setShowCandidates] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [focus, setFocus] = useState<Focus>('none');
  const g = useGraph(run, view);
  const prov = useProvenance(focus === 'provenance' ? selected : null, run);
  const pe = useProvenanceEvidence(view === 'information' || view === 'all' ? run : undefined);

  const nodes = useMemo(
    () => (g.data?.nodes ?? []).filter((n) => kinds[n.type === 'artifact' ? 'instance' : n.type]),
    [g.data, kinds],
  );
  const visible = useMemo(() => new Set(nodes.map((n) => n.node)), [nodes]);
  const relations = useMemo(
    () =>
      (g.data?.relations ?? []).filter(
        (r) =>
          (showCandidates || !isNonFlow(r)) &&
          r.tail.some((t) => visible.has(t)) &&
          r.head.some((h) => visible.has(h)),
      ),
    [g.data, visible, showCandidates],
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
                    setKinds({ event: true, instance: v !== 'execution', entity: false });
                  }}
                  className={`rounded border px-2 py-0.5 ${view === v ? 'border-zinc-400 text-zinc-100' : 'border-zinc-700 text-zinc-500'}`}
                >
                  {v}
                </button>
              ))}
              <span className="mx-2 text-zinc-600">|</span>
              {(['event', 'instance', 'entity'] as const).map((k) => (
                <label key={k} className="flex items-center gap-1 text-zinc-400">
                  <input
                    type="checkbox"
                    checked={kinds[k]}
                    onChange={(e) => setKinds({ ...kinds, [k]: e.target.checked })}
                  />{' '}
                  {k === 'instance' ? 'values' : k === 'entity' ? 'entities' : 'events'}
                </label>
              ))}
              <label className="flex items-center gap-1 text-zinc-400">
                <input
                  type="checkbox"
                  checked={showCandidates}
                  onChange={(e) => setShowCandidates(e.target.checked)}
                />{' '}
                ambiguous candidates
              </label>
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
              <span>
                ━ declared · ╌ inferred (best-effort) · ┈ ambiguous candidate / similarity (not a
                flow) · opacity = evidence strength
              </span>
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
            {pe.data?.summary && (
              <Panel title="information evidence">
                <div className="space-y-1 font-mono text-[11px] text-zinc-400">
                  <div>
                    declared (high-fidelity) share{' '}
                    {pe.data.summary.high_fidelity_share === null
                      ? 'n/a'
                      : `${Math.round(pe.data.summary.high_fidelity_share * 100)}%`}
                  </div>
                  <div>
                    consumed values:{' '}
                    {Object.entries(pe.data.summary.consumed_values)
                      .map(([k, v]) => `${k.toLowerCase()} ${v}`)
                      .join(' · ')}
                  </div>
                  <div>
                    by strength:{' '}
                    {Object.entries(pe.data.summary.relations_by_strength)
                      .map(([k, v]) => `${k.toLowerCase()} ${v}`)
                      .join(' · ')}
                  </div>
                </div>
                {pe.data.ambiguous.length > 0 && (
                  <div className="mt-2 space-y-1">
                    <p className="text-[11px] text-amber-300/90">
                      {pe.data.ambiguous.length} value(s) with ambiguous sources: the evidence fits
                      several producers, so none is chosen. Declaring inputs removes the ambiguity.
                    </p>
                    {pe.data.ambiguous.slice(0, 12).map((a) => (
                      <button
                        key={a.record_id}
                        onClick={() => setSelected(a.target)}
                        className="block w-full truncate text-left font-mono text-[10px] text-zinc-300 hover:underline"
                      >
                        {a.target.slice(0, 18)}… ← {a.candidates.length} candidates
                        {a.certain_sources.length > 0 && ` · ${a.certain_sources.length} certain`}
                      </button>
                    ))}
                  </div>
                )}
              </Panel>
            )}
            {selectedEvent ? (
              <EventInspector
                eventId={selectedEvent}
                runId={run}
                onSelect={(id) => setSelected(`event:${id}`)}
              />
            ) : (
              selected && (
                <Panel title="value">
                  {(() => {
                    const n = g.data?.nodes.find((x) => x.node === selected);
                    if (!n) return null;
                    return (
                      <div className="space-y-1">
                        <Mono>{n.label}</Mono>
                        {n.erased ? (
                          <p className="text-[11px] text-rose-400">
                            erased: the data subject was crypto-shredded
                          </p>
                        ) : (
                          <p className="break-all text-[11px] text-zinc-500">{n.preview}</p>
                        )}
                        {n.content_id && (
                          <p className="font-mono text-[10px] text-zinc-500">
                            content {n.content_id.slice(0, 12)}
                            {(n.same_content_instances ?? 0) > 1 &&
                              ` · same bytes as ${(n.same_content_instances ?? 1) - 1} other value(s) — a distinct value all the same`}
                          </p>
                        )}
                        {n.producer_event && (
                          <button
                            className="font-mono text-[10px] text-sky-300 hover:underline"
                            onClick={() => setSelected(`event:${n.producer_event}`)}
                          >
                            produced by {n.producer_event.slice(0, 8)}
                          </button>
                        )}
                        {n.consumer_event && (
                          <button
                            className="font-mono text-[10px] text-sky-300 hover:underline"
                            onClick={() => setSelected(`event:${n.consumer_event}`)}
                          >
                            consumed by {n.consumer_event.slice(0, 8)} (no observed producer)
                          </button>
                        )}
                      </div>
                    );
                  })()}
                </Panel>
              )
            )}
          </div>
        </div>
      )}
    </Shell>
  );
}
