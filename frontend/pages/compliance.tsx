import { Download, FileCheck } from "lucide-react";
import { API_BASE_URL } from "../lib/api/config";
import { useComplianceStatus } from "../lib/api/hooks/useCompliance";

interface ComplianceStatus {
  framework: string;
  status: "compliant" | "partial" | "non_compliant" | string;
  score?: number;
  controls_met?: number;
  controls_total?: number;
}

const FRAMEWORKS = ["soc2", "gdpr", "hipaa", "eu_ai_act", "iso42001"];

export default function CompliancePage() {
  const { compliance, isComplianceLoading: isLoading } = useComplianceStatus();
  const data = compliance as unknown as ComplianceStatus[] | undefined;

  const items: ComplianceStatus[] =
    data ?? FRAMEWORKS.map((f) => ({ framework: f, status: "unknown" }));

  const exportFramework = (framework: string) => {
    window.open(
      `${API_BASE_URL}/governance/compliance/export?framework=${framework}`,
      "_blank",
    );
  };

  return (
    <div
      style={{
        padding: 24,
        fontFamily: "ui-sans-serif, system-ui",
        background: "#0b1020",
        color: "#e5e7eb",
        minHeight: "100vh",
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: 24,
        }}
      >
        <FileCheck size={28} color="#34d399" />
        <h1 style={{ margin: 0, fontSize: 24 }}>Compliance</h1>
      </header>

      {isLoading && <p style={{ color: "#9ca3af" }}>Loading…</p>}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: 16,
        }}
      >
        {items.map((item) => (
          <div
            key={item.framework}
            style={{ padding: 18, background: "#0f172a", borderRadius: 12 }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <h3
                style={{ margin: 0, fontSize: 16, textTransform: "uppercase" }}
              >
                {item.framework.replace("_", " ")}
              </h3>
              <button
                onClick={() => exportFramework(item.framework)}
                style={{
                  display: "flex",
                  gap: 4,
                  alignItems: "center",
                  background: "transparent",
                  border: "1px solid #1f2937",
                  color: "#a5b4fc",
                  padding: "4px 10px",
                  borderRadius: 6,
                  cursor: "pointer",
                  fontSize: 12,
                }}
              >
                <Download size={14} /> Export
              </button>
            </div>
            <div
              style={{
                marginTop: 12,
                padding: "4px 10px",
                background:
                  item.status === "compliant"
                    ? "#064e3b"
                    : item.status === "partial"
                      ? "#78350f"
                      : item.status === "non_compliant"
                        ? "#7f1d1d"
                        : "#1f2937",
                borderRadius: 4,
                display: "inline-block",
                fontSize: 12,
                textTransform: "uppercase",
              }}
            >
              {item.status}
            </div>
            {typeof item.score === "number" && (
              <div style={{ fontSize: 32, fontWeight: 800, marginTop: 12 }}>
                {(item.score * 100).toFixed(0)}
                <span style={{ fontSize: 16, color: "#9ca3af" }}>%</span>
              </div>
            )}
            {item.controls_total && (
              <div style={{ fontSize: 12, color: "#9ca3af", marginTop: 4 }}>
                {item.controls_met} / {item.controls_total} controls
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
