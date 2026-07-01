import React, { useState, useEffect } from "react";
import MetricCard from "../components/MetricCard";
import SkeletonLoader from "../components/SkeletonLoader";

export const DashboardDemo: React.FC = () => {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 2000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div style={{ padding: "40px", background: "#0a0a0a", minHeight: "100vh" }}>
      <h1 style={{ color: "#fff", marginBottom: "24px" }}>AgentWatch Analytics Demo</h1>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "20px", marginBottom: "40px" }}>
        <MetricCard title="Total Instrumented Sessions" value="2,410" change="+12.4%" isLoading={loading} />
        <MetricCard title="Entitlement Failures Blocked" value="42" change="-2.1%" isLoading={loading} />
        <MetricCard title="Average Latency Reduction" value="184ms" change="+8.3%" isLoading={loading} />
      </div>

      <h2 style={{ color: "#fff", marginBottom: "16px" }}>Detailed Audits</h2>
      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          <SkeletonLoader height="40px" />
          <SkeletonLoader height="40px" />
          <SkeletonLoader height="40px" />
        </div>
      ) : (
        <div style={{ color: "rgba(255,255,255,0.7)" }}>
          Audit logs loaded successfully. No anomalies detected.
        </div>
      )}
    </div>
  );
};

export default DashboardDemo;
