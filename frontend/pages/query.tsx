import Link from 'next/link';
import { useState } from 'react';

import { Shell } from '../components/v3/Shell';
import { ErrorBox, Json, Label, Panel } from '../components/v3/ui';
import { useQueryAsk } from '../lib/v3/client';

const EXAMPLES = [
  'why did latest take longer than latest~1?',
  'where did report.md come from?',
  'what depends on report.md?',
  'runs status=ERROR',
  'motifs latest',
];

/** QUERY — questions are compiled to structured queries; answers only restate results and cite evidence. */
export default function Query() {
  const [text, setText] = useState('');
  const ask = useQueryAsk();
  const a = ask.data;
  return (
    <Shell title="QUERY">
      <Panel title="ask">
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (text.trim()) ask.mutate(text);
          }}
        >
          <input
            aria-label="question"
            className="flex-1 rounded border border-zinc-700 bg-zinc-900 px-3 py-2 font-mono text-sm"
            placeholder="why did run B take longer than run A?"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <button className="rounded bg-sky-800 px-4 font-mono text-sm">ask</button>
        </form>
        <div className="mt-2 flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => {
                setText(ex);
                ask.mutate(ex);
              }}
              className="rounded border border-zinc-800 px-2 py-0.5 font-mono text-[11px] text-zinc-400 hover:text-zinc-100"
            >
              {ex}
            </button>
          ))}
        </div>
        <p className="mt-2 text-[11px] text-zinc-500">
          Questions are mapped deterministically to structured queries (runs, events, provenance,
          dependents, compare, motifs, causes, effects, genome, drift). No language model authors
          facts; every answer lists the evidence it rests on.
        </p>
      </Panel>
      <ErrorBox error={ask.error} />
      {a && (
        <div className="mt-3 grid grid-cols-12 gap-3">
          <Panel
            title="answer"
            className="col-span-12 lg:col-span-7"
            right={
              a.structured_query && (
                <Label>
                  {a.structured_query} · {a.compiled_by}
                </Label>
              )
            }
          >
            {a.answered ? (
              <pre className="whitespace-pre-wrap font-mono text-[12px] leading-relaxed text-zinc-200">
                {(a.answer as string[]).join('\n')}
              </pre>
            ) : (
              <p className="text-sm text-amber-300">{a.message}</p>
            )}
          </Panel>
          <Panel
            title={`evidence (${(a.evidence ?? []).length})`}
            className="col-span-12 lg:col-span-5"
          >
            <div className="flex max-h-60 flex-wrap gap-1 overflow-auto">
              {(a.evidence as string[]).map((ev) => {
                const id = ev.replace(/^(event|artifact):/, '');
                return ev.startsWith('artifact:') ? (
                  <Label key={ev} tone="sky">
                    {ev.slice(0, 20)}
                  </Label>
                ) : (
                  <Link
                    key={ev}
                    href={`/timeline?event=${id}`}
                    className="rounded border border-zinc-700 px-1.5 font-mono text-[10px] text-zinc-300 hover:border-zinc-400"
                  >
                    {ev.slice(0, 20)}
                  </Link>
                );
              })}
            </div>
            {a.result && (
              <details className="mt-2">
                <summary className="cursor-pointer font-mono text-[11px] text-zinc-500">
                  structured result
                </summary>
                <Json value={a.result} max={6000} />
              </details>
            )}
          </Panel>
        </div>
      )}
    </Shell>
  );
}
