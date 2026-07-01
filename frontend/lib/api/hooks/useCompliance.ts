import { api } from "../config";

interface ComplianceStatus {
  overall_score: number;
  frameworks: Array<{
    name: string;
    score: number;
    controls_passed: number;
    controls_total: number;
  }>;
  last_evaluated: string;
  issues: Array<{ control: string; severity: string; description: string }>;
}

export const useComplianceStatus = () => {
  const query = api.useQuery<ComplianceStatus>({
    url: "/governance/compliance/status",
    key: ["governance", "compliance", "status"],
  });
  return {
    compliance: query.data,
    isComplianceLoading: query.isLoading,
    complianceError: query.error,
    ...query,
  };
};
