import type {
  BlockedEventsResponse,
  DashboardSummary,
  SessionsResponse,
} from "../../api";
import { api } from "../config";

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
  const query = api.useQuery<SessionsResponse>({
    url: "/sessions",
    key: ["sessions"],
  });
  return {
    sessions: query.data?.sessions ?? [],
    isSessionsLoading: query.isLoading,
    sessionsError: query.error,
    ...query,
  };
};

export const useBlockedEvents = () => {
  const query = api.useQuery<BlockedEventsResponse>({
    url: "/safety/blocked",
    key: ["safety", "blocked"],
  });
  return {
    blockedEvents: query.data?.blocked_events ?? [],
    isBlockedLoading: query.isLoading,
    blockedError: query.error,
    ...query,
  };
};
