import { useState } from 'react';

import { useEvent, useProvenance } from '../../lib/v3/client';
import type { InfoEvidenceAttrs } from '../../lib/v3/types';
import { ErrorBox, Json, Label, Maturity, Mono, Panel, Status, fmtMs, short } from './ui';

/** Everything known about one event: normalized form, raw evidence, relations, provenance, motifs. */
export function EventInspector({
  eventId,
  runId,
  onSelect,
}: {
  eventId: string | null;
  runId?: string;
  onSelect?: (eventId: string) => void;
}) {
  const q = useEvent(eventId);
  const [tab, setTab] = useState<'event' | 'evidence' | 'relations' | 'provenance'>('event');
  const prov = useProvenance(tab === 'provenance' && eventId ? `event:${eventId}` : null, runId);
  if (!eventId)
    return (
      <Panel title="inspector">
        <p className="text-sm text-zinc-500">Select an event.</p>
      </Panel>
    );
  if (q.error)
    return (
      <Panel title="inspector">
        <ErrorBox error={q.error} />
      </Panel>
    );
  const d = q.data;
  if (!d)
    return (
      <Panel title="inspector">
        <p className="text-sm text-zinc-500">loading…</p>
      </Panel>
    );
  const e = d.event;
  return (
    <Panel
      title={`event ${short(e.event_id)}`}
      right={<Mono className="text-zinc-500">{e.normalizer}</Mono>}
    >
      <div className="mb-2 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <Label tone="sky">{e.kind}</Label>
          <span className="font-mono text-sm">{e.operation}</span>
          <Status s={e.status} />
          <Mono className="text-zinc-500">{fmtMs(e.time.duration_ms)}</Mono>
        </div>
        <div className="font-mono text-[11px] text-zinc-400">
          actor {e.actor ?? <em className="text-amber-400">missing</em>} · object {e.object ?? '—'}{' '}
          · run {short(e.run_id)} ({e.run_basis})
        </div>
        {e.missing.length > 0 && (
          <div
            className="font-mono text-[11px] text-amber-400/90"
            title="facts the source did not provide; never invented"
          >
            missing: {e.missing.join(', ')}
          </div>
        )}
        <div className="font-mono text-[11px] text-zinc-500">
          confidence: observation {e.confidence.observation.value} ({e.confidence.observation.basis}
          ) · attribution {e.confidence.attribution.value} ({e.confidence.attribution.basis}){' '}
          {!e.confidence.observation.calibrated && (
            <span className="text-zinc-600">uncalibrated</span>
          )}
        </div>
      </div>
      <div className="mb-2 flex gap-1 font-mono text-[11px]">
        {(['event', 'evidence', 'relations', 'provenance'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded px-2 py-0.5 ${tab === t ? 'bg-zinc-800 text-zinc-100' : 'text-zinc-500 hover:text-zinc-200'}`}
          >
            {t}
          </button>
        ))}
      </div>
      {tab === 'event' && (
        <div className="space-y-2">
          {d.motifs.length > 0 && (
            <div className="space-y-1">
              {d.motifs.map((m) => (
                <div key={m.record_id} className="font-mono text-[11px] text-violet-300">
                  {m.motif_id} {m.motif_name}: {m.explanation} <Maturity m={m.maturity} />
                </div>
              ))}
            </div>
          )}
          <Json
            value={{
              inputs: e.inputs,
              outputs: e.outputs,
              effects: e.effects,
              resources: e.resources,
              attributes: e.attributes,
              error: e.error,
              parents: e.parents,
              time: e.time,
            }}
          />
        </div>
      )}
      {tab === 'evidence' && (
        <div className="space-y-2">
          <p className="text-[11px] text-zinc-500">
            Immutable raw observations this event was derived from.
          </p>
          {d.evidence.map((o) => (
            <div key={o.obs_id} className="space-y-1">
              <div className="font-mono text-[11px] text-zinc-400">
                {o.obs_id} · {o.source_kind} · sha256 {o.payload_sha256.slice(0, 12)} · segment{' '}
                {o.segment_id ?? 'unsealed'}
                {o.redaction && <span className="ml-1 text-amber-400">redacted</span>}
                {o.encoding === 'erased' && (
                  <span
                    className="ml-1 text-rose-400"
                    title="the data subject was erased (crypto-shredded); this payload cannot be recovered"
                  >
                    erased
                  </span>
                )}
              </div>
              <Json
                value={{
                  declared_ids: o.declared_ids,
                  observed_at: o.observed_at,
                  payload: o.payload,
                }}
                max={2500}
              />
            </div>
          ))}
        </div>
      )}
      {tab === 'relations' && (
        <div className="space-y-1 font-mono text-[11px]">
          {[
            ...d.incoming.map((r) => ({ r, dir: '←' })),
            ...d.outgoing.map((r) => ({ r, dir: '→' })),
          ].map(({ r, dir }) => (
            <div key={r.rel_id + dir} className="flex items-center gap-2">
              <span className="text-zinc-500">{dir}</span>
              <Label
                tone={r.view === 'INFORMATION' ? 'sky' : r.view === 'CAUSAL' ? 'amber' : 'zinc'}
              >
                {r.type}
              </Label>
              <span className="text-zinc-500">
                {(r.attributes as InfoEvidenceAttrs)?.evidence_type ? (
                  <>
                    {String((r.attributes as InfoEvidenceAttrs).evidence_type).toLowerCase()} ·{' '}
                    {(r.attributes as InfoEvidenceAttrs).strength}
                    {(r.attributes as InfoEvidenceAttrs).resolution === 'AMBIGUOUS' && (
                      <span className="ml-1 text-amber-400">ambiguous</span>
                    )}
                  </>
                ) : (
                  <>
                    {r.basis.toLowerCase()}
                    {r.basis !== 'DECLARED' ? ` ${r.confidence}` : ''}
                  </>
                )}
              </span>
              <button
                className="truncate text-left text-zinc-200 hover:underline"
                onClick={() => r.other.type === 'event' && onSelect?.(r.other.node.slice(6))}
              >
                {r.other.label}
              </button>
            </div>
          ))}
        </div>
      )}
      {tab === 'provenance' && (
        <div>
          <ErrorBox error={prov.error} />
          {prov.data ? (
            <>
              <pre className="max-h-96 overflow-auto whitespace-pre font-mono text-[11px] leading-snug text-zinc-300">
                {(prov.data.text as string[]).join('\n')}
              </pre>
              <p className="mt-1 text-[11px] text-zinc-500">
                lineage metrics are EXPERIMENTAL: {JSON.stringify(prov.data.metrics)}
              </p>
            </>
          ) : (
            !prov.error && <p className="text-sm text-zinc-500">loading…</p>
          )}
        </div>
      )}
    </Panel>
  );
}
