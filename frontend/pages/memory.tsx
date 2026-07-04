import { AlertTriangle, Brain, Database } from "lucide-react";
import { useState } from "react";
import { useMemoryGraph, useMemoryQuery } from "../lib/api/hooks/useMemory";

export default function MemoryPage() {
  const [query, setQuery] = useState("");
  const { graph, isGraphLoading } = useMemoryGraph();
  const { queryResults } = useMemoryQuery(query);

  const nodes = graph?.nodes ?? [];
  const edges = graph?.edges ?? [];
  const corrupted = nodes.filter((n) => n.kind === "corrupted");

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
        <Brain size={28} color="#60a5fa" />
        <h1 style={{ margin: 0, fontSize: 24 }}>Memory Visualization</h1>
      </header>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 16,
          marginBottom: 24,
        }}
      >
        <Stat
          label="Total memories"
          value={nodes.length}
          icon={<Database size={18} />}
        />
        <Stat
          label="Retrieval edges"
          value={edges.length}
          icon={<Database size={18} />}
        />
        <Stat
          label="Corrupted / stale"
          value={corrupted.length}
          icon={
            <AlertTriangle
              size={18}
              color={corrupted.length ? "#dc2626" : "#9ca3af"}
            />
          }
        />
      </div>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>
          Natural-language query
        </h2>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder='e.g. "what did we decide about the database last week?"'
          style={{
            width: "100%",
            padding: 12,
            borderRadius: 8,
            border: "1px solid #1f2937",
            background: "#0f172a",
            color: "#e5e7eb",
          }}
        />
        {queryResults && queryResults.length > 0 && (
          <ul style={{ listStyle: "none", padding: 0, marginTop: 12 }}>
            {queryResults.map((r, i) => (
              <li
                key={i}
                style={{
                  padding: 10,
                  borderRadius: 6,
                  background: "#0f172a",
                  marginBottom: 6,
                }}
              >
                <code style={{ color: "#a5b4fc" }}>
                  {String(r.key ?? r.id ?? i)}
                </code>
                <span style={{ marginLeft: 8 }}>{String(r.value ?? "")}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>Memory nodes</h2>
        {isGraphLoading && <p style={{ color: "#9ca3af" }}>Loading…</p>}
        {!isGraphLoading && nodes.length === 0 && (
          <p style={{ color: "#9ca3af" }}>
            No memories captured yet. Run a session to populate.
          </p>
        )}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: 12,
          }}
        >
          {nodes.map((n) => (
            <div
              key={n.id}
              style={{
                padding: 12,
                borderRadius: 8,
                background: "#0f172a",
                borderLeft: `4px solid ${n.color}`,
              }}
            >
              <div
                style={{
                  fontSize: 11,
                  color: "#9ca3af",
                  textTransform: "uppercase",
                }}
              >
                {n.kind}
              </div>
              <div style={{ fontWeight: 600, marginTop: 4 }}>{n.label}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function Stat({
  label,
  value,
  icon,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
}) {
  return (
    <div
      style={{
        padding: 16,
        background: "#0f172a",
        borderRadius: 10,
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
      }}
    >
      <div>
        <div style={{ fontSize: 12, color: "#9ca3af" }}>{label}</div>
        <div style={{ fontSize: 28, fontWeight: 700, marginTop: 4 }}>
          {value}
        </div>
      </div>
      {icon}
    </div>
  );
}
