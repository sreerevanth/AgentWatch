// Pure graph utilities for the MAP view: layered layout and cone/path computation.
// Kept free of React so they can be unit-tested.

import type { Relation } from './types';

export interface Edge {
  from: string;
  to: string;
  rel: Relation;
}
export interface Positioned {
  id: string;
  x: number;
  y: number;
  layer: number;
}

export function edgesOf(relations: Relation[]): Edge[] {
  const out: Edge[] = [];
  for (const rel of relations)
    for (const t of rel.tail) for (const h of rel.head) out.push({ from: t, to: h, rel });
  return out;
}

/** Longest-path layering (cycles broken by DFS back-edge removal) + barycenter ordering. */
export function layeredLayout(
  nodes: string[],
  edges: Edge[],
  dx = 220,
  dy = 56,
): Map<string, Positioned> {
  const succ = new Map<string, string[]>();
  const pred = new Map<string, string[]>();
  for (const n of nodes) {
    succ.set(n, []);
    pred.set(n, []);
  }
  // drop back edges found by DFS so layering terminates on cyclic graphs
  const state = new Map<string, number>(); // 0 = unvisited, 1 = on stack, 2 = done
  const keep: Edge[] = [];
  const bySrc = new Map<string, Edge[]>();
  for (const e of edges) {
    if (!succ.has(e.from) || !succ.has(e.to) || e.from === e.to) continue;
    if (!bySrc.has(e.from)) bySrc.set(e.from, []);
    bySrc.get(e.from)!.push(e);
  }
  const visit = (root: string) => {
    const stack: [string, number][] = [[root, 0]];
    state.set(root, 1);
    while (stack.length) {
      const top = stack[stack.length - 1];
      const list = bySrc.get(top[0]) ?? [];
      if (top[1] < list.length) {
        const e = list[top[1]++];
        const s = state.get(e.to) ?? 0;
        if (s === 1) continue; // back edge
        keep.push(e);
        if (s === 0) {
          state.set(e.to, 1);
          stack.push([e.to, 0]);
        }
      } else {
        state.set(top[0], 2);
        stack.pop();
      }
    }
  };
  for (const n of nodes) if (!state.get(n)) visit(n);
  for (const e of keep) {
    succ.get(e.from)!.push(e.to);
    pred.get(e.to)!.push(e.from);
  }
  // longest path from sources (Kahn order)
  const indeg = new Map(nodes.map((n) => [n, pred.get(n)!.length]));
  const layer = new Map(nodes.map((n) => [n, 0]));
  const queue = nodes.filter((n) => indeg.get(n) === 0);
  while (queue.length) {
    const n = queue.shift()!;
    for (const m of succ.get(n)!) {
      layer.set(m, Math.max(layer.get(m)!, layer.get(n)! + 1));
      indeg.set(m, indeg.get(m)! - 1);
      if (indeg.get(m) === 0) queue.push(m);
    }
  }
  const layers: string[][] = [];
  for (const n of nodes) {
    const l = layer.get(n)!;
    (layers[l] ??= []).push(n);
  }
  // one barycenter sweep to reduce crossings
  const order = new Map<string, number>();
  layers.forEach((ns, l) => {
    if (l > 0) {
      const bc = (n: string) => {
        const ps = pred.get(n)!.filter((p) => order.has(p));
        return ps.length
          ? ps.reduce((a, p) => a + order.get(p)!, 0) / ps.length
          : Number.MAX_SAFE_INTEGER;
      };
      ns.sort((a, b) => bc(a) - bc(b) || a.localeCompare(b));
    }
    ns.forEach((n, i) => order.set(n, i));
  });
  const pos = new Map<string, Positioned>();
  layers.forEach((ns, l) =>
    ns.forEach((n, i) =>
      pos.set(n, { id: n, layer: l, x: l * dx, y: i * dy - ((ns.length - 1) * dy) / 2 }),
    ),
  );
  return pos;
}

/** Nodes reachable from `start` following edges forward ("down") or backward ("up"). */
export function cone(
  start: string,
  edges: Edge[],
  direction: 'up' | 'down',
  types?: Set<string>,
): Set<string> {
  const adj = new Map<string, string[]>();
  for (const e of edges) {
    if (types && !types.has(e.rel.type)) continue;
    const [a, b] = direction === 'down' ? [e.from, e.to] : [e.to, e.from];
    if (!adj.has(a)) adj.set(a, []);
    adj.get(a)!.push(b);
  }
  const seen = new Set<string>([start]);
  const stack = [start];
  while (stack.length) {
    const n = stack.pop()!;
    for (const m of adj.get(n) ?? []) {
      if (!seen.has(m)) {
        seen.add(m);
        stack.push(m);
      }
    }
  }
  return seen;
}

export const EVIDENCE_COLOR: Record<string, string> = {
  CORRELATIONAL: '#a1a1aa',
  OBSERVATIONAL: '#60a5fa',
  QUASI_CAUSAL: '#a78bfa',
  INTERVENTIONAL: '#f59e0b',
  VERIFIED: '#22c55e',
};

export const VIEW_COLOR: Record<string, string> = {
  EXECUTION: '#94a3b8',
  INFORMATION: '#38bdf8',
  CAUSAL: '#f59e0b',
};

/** Opacity encodes confidence; undeclared (inferred) relations are dashed. */
export function edgeStyle(rel: Relation): {
  stroke: string;
  opacity: number;
  dash: string | undefined;
} {
  const stroke =
    rel.view === 'CAUSAL' && rel.evidence_class
      ? (EVIDENCE_COLOR[rel.evidence_class] ?? VIEW_COLOR.CAUSAL)
      : (VIEW_COLOR[rel.view] ?? '#94a3b8');
  return {
    stroke,
    opacity: 0.25 + 0.75 * Math.max(0, Math.min(1, rel.confidence)),
    dash: rel.basis === 'DECLARED' ? undefined : '5 4',
  };
}
