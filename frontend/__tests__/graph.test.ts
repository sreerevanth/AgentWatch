import { cone, edgeStyle, edgesOf, layeredLayout } from '../lib/v3/graph';
import type { Relation } from '../lib/v3/types';

const rel = (tail: string[], head: string[], extra: Partial<Relation> = {}): Relation => ({
  rel_id: `${tail.join()}->${head.join()}`,
  view: 'EXECUTION',
  type: 'CONTAINS',
  tail,
  head,
  basis: 'DECLARED',
  evidence_class: null,
  confidence: 1,
  run_id: 'r',
  evidence: [],
  derived_by: 't',
  attributes: {},
  ...extra,
});

describe('edgesOf', () => {
  it('expands hyperedges into tail x head pairs', () => {
    const e = edgesOf([rel(['a', 'b'], ['c'])]);
    expect(e.map((x) => `${x.from}>${x.to}`)).toEqual(['a>c', 'b>c']);
  });
});

describe('layeredLayout', () => {
  it('places children in later layers than parents (longest path)', () => {
    const edges = edgesOf([rel(['a'], ['b']), rel(['b'], ['c']), rel(['a'], ['c'])]);
    const pos = layeredLayout(['a', 'b', 'c'], edges);
    expect(pos.get('a')!.layer).toBe(0);
    expect(pos.get('b')!.layer).toBe(1);
    expect(pos.get('c')!.layer).toBe(2);
  });

  it('terminates on cycles and keeps every node', () => {
    const edges = edgesOf([rel(['a'], ['b']), rel(['b'], ['a']), rel(['b'], ['c'])]);
    const pos = layeredLayout(['a', 'b', 'c'], edges);
    expect(pos.size).toBe(3);
    expect(pos.get('c')!.layer).toBeGreaterThan(pos.get('a')!.layer);
  });
});

describe('cone', () => {
  const edges = edgesOf([
    rel(['a'], ['b']),
    rel(['b'], ['c']),
    rel(['x'], ['c'], { type: 'DERIVES_FROM', view: 'INFORMATION' }),
  ]);
  it('collects ancestors and descendants', () => {
    expect([...cone('c', edges, 'up')].sort()).toEqual(['a', 'b', 'c', 'x']);
    expect([...cone('a', edges, 'down')].sort()).toEqual(['a', 'b', 'c']);
  });
  it('can restrict relation types', () => {
    expect([...cone('c', edges, 'up', new Set(['CONTAINS']))].sort()).toEqual(['a', 'b', 'c']);
  });
});

describe('edgeStyle', () => {
  it('dashes inferred relations and scales opacity with confidence', () => {
    const inferred = edgeStyle(
      rel(['a'], ['b'], { basis: 'CONTENT_MATCH', confidence: 0.6, view: 'INFORMATION' }),
    );
    expect(inferred.dash).toBeDefined();
    expect(inferred.opacity).toBeCloseTo(0.25 + 0.75 * 0.6);
    expect(edgeStyle(rel(['a'], ['b'])).dash).toBeUndefined();
  });
  it('colours causal relations by evidence class', () => {
    expect(
      edgeStyle(rel(['a'], ['b'], { view: 'CAUSAL', evidence_class: 'VERIFIED' })).stroke,
    ).toBe('#22c55e');
  });
});
