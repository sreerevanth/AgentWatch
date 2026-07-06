import { api } from "../config";

interface OwaspFinding {
  vector: string;
  severity: string;
  detail: string;
  event_id: string;
}

interface OwaspScan {
  score: number;
  findings: OwaspFinding[];
}

export interface SandboxResult {
  command: string;
  blocked: boolean;
  risk_score: number;
  blast_radius_score: number;
  policy_action: string;
  exfil_findings: string[];
  injection_findings: string[];
  explanation: string;
  threat_path: string[];
}

interface SandboxBody {
  command: string;
  environment?: Record<string, string>;
}

export const useOwaspScan = () => {
  const query = api.useQuery<OwaspScan>({
    url: "/security/owasp",
    key: ["security", "owasp"],
  });
  return {
    owaspScan: query.data,
    isOwaspLoading: query.isLoading,
    owaspError: query.error,
    ...query,
  };
};

export const useSandboxSimulate = () => {
  const mutation = api.useMutation<SandboxResult, Error, SandboxBody>({
    url: "/security/sandbox/simulate",
    method: "POST",
  });
  return {
    simulateSandbox: mutation.mutateAsync,
    isSandboxSimulating: mutation.isPending,
    sandboxResult: mutation.data,
    ...mutation,
  };
};
