import { api } from "../config";

interface MemoryNode {
  id: string;
  label: string;
  kind: string;
  color: string;
  metadata?: Record<string, string | number | boolean | null>;
}

interface MemoryEdge {
  src: string;
  dst: string;
  kind: string;
}

interface MemoryGraph {
  nodes: MemoryNode[];
  edges: MemoryEdge[];
}

interface MemoryQueryEntry {
  key?: string;
  id?: string;
  value?: string;
  [key: string]: string | number | boolean | null | undefined;
}

export const useMemoryGraph = () => {
  const query = api.useQuery<MemoryGraph>({
    url: "/memory/graph",
    key: ["memory", "graph"],
  });
  return {
    graph: query.data,
    isGraphLoading: query.isLoading,
    graphError: query.error,
    ...query,
  };
};

export const useMemoryQuery = (queryText: string) => {
  const query = api.useQuery<MemoryQueryEntry[]>({
    url: "/memory/query",
    key: ["memory", "query", queryText],
    params: { q: queryText },
    enabled: !!queryText,
  });
  return {
    queryResults: query.data,
    isQueryLoading: query.isLoading,
    queryError: query.error,
    ...query,
  };
};
