import { api } from "../config";

interface CostSummary {
  total_cost_usd: number;
  by_model: Record<string, number>;
  by_session: Array<{ session_id: string; cost_usd: number }>;
  period: string;
}

export const useCostSummary = () => {
  const query = api.useQuery<CostSummary>({
    url: "/cost/summary",
    key: ["cost", "summary"],
  });
  return {
    costSummary: query.data,
    isCostLoading: query.isLoading,
    costError: query.error,
    ...query,
  };
};
