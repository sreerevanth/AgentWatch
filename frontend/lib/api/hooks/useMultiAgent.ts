import { api } from "../config";

interface DagNode {
  node_id: string;
  agent_id: string;
  action: string;
  timestamp: string;
}

interface DagEdge {
  src: string;
  dst: string;
  kind: string;
}

interface DagResponse {
  nodes: DagNode[];
  edges: DagEdge[];
}

interface DeadlockReport {
  deadlocked: boolean;
  cycle: string[];
  detail: string;
}

export const useOrchestrationDag = () => {
  const query = api.useQuery<DagResponse>({
    url: "/orchestration/dag",
    key: ["orchestration", "dag"],
  });
  return {
    dag: query.data,
    isDagLoading: query.isLoading,
    dagError: query.error,
    ...query,
  };
};

export const useDeadlockDetection = () => {
  const query = api.useQuery<DeadlockReport>({
    url: "/orchestration/deadlock",
    key: ["orchestration", "deadlock"],
  });
  return {
    deadlock: query.data,
    isDeadlockLoading: query.isLoading,
    deadlockError: query.error,
    ...query,
  };
};
