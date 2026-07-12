import type { AgentSession, DashboardSummary } from "../../api";
import { api } from "../config";

interface BlockedEvent {
  event_id: string;
  session_id: string;
  agent_id: string;
  timestamp: string;
  risk_level: string;
  reasons: string[];
}

export const useDashboardSummary = () => {
  const query = api.useQuery<DashboardSummary>({
    url: "/dashboard/summary",
    key: ["dashboard", "summary"],
  });
  return {
    summary: query.data,
    isSummaryLoading: query.isLoading,
    summaryError: query.error,
    ...query,
  };
};

export const useSessions = () => {
  const query = api.useQuery<AgentSession[]>({
    url: "/sessions",
    key: ["sessions"],
  });
  return {
    sessions: query.data ?? [],
    isSessionsLoading: query.isLoading,
    sessionsError: query.error,
    ...query,
  };
};

export const useBlockedEvents = () => {
  const query = api.useQuery<BlockedEvent[]>({
    url: "/safety/blocked",
    key: ["safety", "blocked"],
  });
  return {
    blockedEvents: query.data ?? [],
    isBlockedLoading: query.isLoading,
    blockedError: query.error,
    ...query,
  };
};
