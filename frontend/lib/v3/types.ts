// Types mirroring the AgentWatch v3 API (agentwatch/api/v3.py). The frontend renders the
// canonical v3 model as served; it never re-derives interpretations of its own.

export type EventKind =
  | 'MODEL_INVOCATION'
  | 'TOOL_INVOCATION'
  | 'RETRIEVAL'
  | 'MEMORY_ACCESS'
  | 'MESSAGE'
  | 'DELEGATION'
  | 'TRANSFORMATION'
  | 'STATE_MUTATION'
  | 'EXTERNAL_IO'
  | 'EXTERNAL_INPUT'
  | 'SYNCHRONIZATION'
  | 'OPERATION'
  | 'LIFECYCLE'
  | 'FAILURE'
  | 'RECOVERY'
  | 'UNKNOWN';

export interface Confidence {
  value: number;
  basis: string;
  calibrated: boolean;
}

export interface ArtifactRef {
  artifact_id: string;
  role: string;
  label: string | null;
}

export interface CEvent {
  event_id: string;
  interp_id: string;
  normalizer: string;
  derived_from: string[];
  kind: EventKind;
  operation: string;
  status: 'OK' | 'ERROR' | 'TIMEOUT' | 'CANCELLED' | 'UNKNOWN';
  actor: string | null;
  object: string | null;
  facets: string[];
  inputs: ArtifactRef[];
  outputs: ArtifactRef[];
  effects: { kind: string; target: string; target_type: string }[];
  time: {
    start: string | null;
    end: string | null;
    basis: string;
    duration_ms: number | null;
    ordering_key: string;
  };
  source_ids: [string, string][];
  parents: { relation: string; key_space: string; value: string }[];
  run_key: [string, string] | null;
  run_id: string | null;
  run_basis: string | null;
  error: Record<string, unknown> | null;
  resources: Record<string, number>;
  attributes: Record<string, unknown>;
  confidence: { observation: Confidence; attribution: Confidence };
  missing: string[];
}

export interface Run {
  run_id: string;
  name: string | null;
  status: string;
  status_basis: string;
  started_at: string | null;
  ended_at: string | null;
  duration_ms: number | null;
  event_count: number;
  error_events: number;
  kinds: Record<string, number>;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  attributes: Record<string, unknown>;
  fingerprint: Record<string, unknown>;
  system_version: string;
  declared_links: number;
  resolved_links: number;
  completeness: number;
  unresolved_links: { event_id: string; relation: string; key_space: string; value: string }[];
}

export type View = 'EXECUTION' | 'INFORMATION' | 'CAUSAL';

export interface Relation {
  rel_id: string;
  view: View;
  type: string;
  tail: string[];
  head: string[];
  basis: string;
  evidence_class: string | null;
  confidence: number;
  run_id: string | null;
  evidence: string[];
  derived_by: string;
  attributes: Record<string, unknown>;
}

export interface NodeDesc {
  node: string;
  type: 'event' | 'artifact' | 'entity';
  label: string;
  actor?: string | null;
  status?: string;
  start?: string | null;
  run_id?: string | null;
  preview?: string | null;
  roles?: string[];
}

export interface GraphResponse {
  run_id: string;
  view: string;
  nodes: NodeDesc[];
  relations: Relation[];
  stats: Record<string, unknown>;
}

export interface MotifInstance {
  record_id: string;
  motif_id: string;
  motif_name: string;
  run_id: string;
  events: string[];
  artifacts: string[];
  confidence: number;
  explanation: string;
  measures: Record<string, unknown>;
  maturity: string;
}

export interface RunDetail {
  run: Run;
  events: CEvent[];
  graph: Record<string, unknown>;
  actors: Record<string, number>;
  tools: Record<string, number>;
  models: Record<string, number>;
  failures: { event_id: string; label: string; error: Record<string, unknown> | null }[];
  retries: number;
  missing_facts: Record<string, number>;
  information: Record<string, number>;
  tree: { depth: number; event_id: string }[];
  motif_instances: MotifInstance[];
  profile: { features: Record<string, number>; motif_counts: Record<string, number> } | null;
}

export interface ObservationDoc {
  obs_id: string;
  source_kind: string;
  sensor: { sensor_type: string; sensor_version: string; instance_id: string };
  observed_at: string | null;
  received_at: string;
  payload_sha256: string;
  declared_ids: Record<string, string>;
  redaction: Record<string, unknown> | null;
  segment_id: string | null;
  payload: unknown;
}

export interface EventDetail {
  event: CEvent;
  evidence: ObservationDoc[];
  incoming: (Relation & { other: NodeDesc })[];
  outgoing: (Relation & { other: NodeDesc })[];
  motifs: MotifInstance[];
}

export interface Divergence {
  type: string;
  operation: string;
  a_event: { event_id: string; label: string; status: string } | null;
  b_event: { event_id: string; label: string; status: string } | null;
  reasons: string[];
  cone: {
    events_in_cone: number;
    events_total: number;
    latency_share: number | null;
    token_share: number | null;
    interpretation: string;
  } | null;
}

export interface CompareResult {
  run_a: Partial<Run>;
  run_b: Partial<Run>;
  identical_structure: boolean;
  earliest_divergence: Divergence | null;
  structural: {
    only_in_a: { signature: string; count: number }[];
    only_in_b: { signature: string; count: number }[];
    edges_only_in_a: string[];
    edges_only_in_b: string[];
    alignment_similarity: number;
  };
  resources: Record<string, { a: number; b: number; delta: number; ratio: number | null }>;
  information: Record<string, { a: number; b: number; delta: number }>;
  motifs: Record<string, { a: number; b: number }>;
  fingerprint: {
    same_system_version: boolean;
    a: Record<string, unknown>;
    b: Record<string, unknown>;
  };
  method: string;
}

export interface Capability {
  name: string;
  version: string;
  maturity: 'EXPERIMENTAL' | 'VALIDATED' | 'PRODUCTION';
  description: string;
  evidence: string[];
}
