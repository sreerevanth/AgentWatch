import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  Film,
  GitBranch,
  History,
  Info,
  Layers,
  MessageSquare,
  Pause,
  Play,
  Search,
  ShieldAlert,
  SkipBack,
  SkipForward,
  Split,
  Wrench,
  XCircle,
  Zap,
} from "lucide-react";
import { useRouter } from "next/router";
import { useEffect, useMemo, useRef, useState } from "react";
import { AgentEvent } from "../lib/api";
import type { SimulationResult } from "../lib/api/hooks/useSessions";
import { useSessionReplay, useSimulate } from "../lib/api/hooks/useSessions";

interface ReplaySession {
  session_id: string;
  goal?: string;
  framework: string;
  status: string;
  steps: {
    index: number;
    event: AgentEvent;
    annotations: string[];
    is_failure_point: boolean;
  }[];
  total_events: number;
  failure_analysis?: any;
  reasoning_audit?: {
    overall_score: number;
    hallucination_risk: number;
    goal_alignment: number;
    findings: {
      type: string;
      severity: string;
      message: string;
      step_index: number;
    }[];
  };
}

const EVENT_COLOR: Record<string, string> = {
  "tool.call": "#3b82f6",
  "tool.result": "#22c55e",
  "tool.error": "#ef4444",
  "planner.output": "#a78bfa",
  "planner.input": "#f472b6",
  "safety.block": "#dc2626",
  "safety.check": "#f59e0b",
  "session.start": "#64748b",
  "session.end": "#64748b",
  "agent.start": "#64748b",
  "agent.end": "#64748b",
  "agent.error": "#ef4444",
  "memory.read": "#10b981",
  "memory.write": "#10b981",
};

const EVENT_ICON: Record<string, any> = {
  "tool.call": Wrench,
  "tool.result": CheckCircle2,
  "tool.error": XCircle,
  "planner.output": MessageSquare,
  "planner.input": Search,
  "safety.block": ShieldAlert,
  "safety.check": ShieldAlert,
  "session.start": Clock,
  "session.end": Clock,
  "agent.start": Zap,
  "agent.end": Zap,
  "agent.error": AlertTriangle,
  "memory.read": Layers,
  "memory.write": Layers,
};

export default function ReplayStudio() {
  const router = useRouter();
  const sessionParam =
    typeof router.query.session === "string" ? router.query.session : "";
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1000);
  const [activeTab, setActiveTab] = useState<
    "details" | "simulation" | "diff" | "analysis"
  >("details");
  const [simResult, setSimResult] = useState<SimulationResult | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [replacementValue, setReplacementValue] = useState("");

  const {
    replay,
    isReplayLoading: isLoading,
    replayError: error,
  } = useSessionReplay(sessionParam || undefined);
  const data = replay as ReplaySession | undefined;
  const { simulate: runSimulate } = useSimulate();
  const steps = data?.steps ?? [];
  const events = useMemo(() => steps.map((s) => s.event), [steps]);

  // Playback logic
  useEffect(() => {
    if (!playing || events.length === 0) return;
    if (step >= events.length - 1) {
      setPlaying(false);
      return;
    }
    const t = setTimeout(() => {
      setStep((s) => Math.min(s + 1, events.length - 1));
    }, playbackSpeed);
    return () => clearTimeout(t);
  }, [playing, step, events.length, playbackSpeed]);

  const currentStep = steps[step];
  const currentEvent = currentStep?.event;

  const handleSimulate = async () => {
    if (!sessionParam) return;
    setIsSimulating(true);
    try {
      const result = await runSimulate({
        sessionId: sessionParam,
        rewind_to_step: step,
        replacement: replacementValue,
        notes: "Studio manual override",
      });
      setSimResult(result);
      setActiveTab("diff");
    } catch (err) {
      console.error("Simulation failed", err);
    } finally {
      setIsSimulating(false);
    }
  };

  if (isLoading)
    return <div className="p-8 text-slate-400">Loading Replay Studio...</div>;
  if (error)
    return (
      <div className="p-8 text-red-400">
        Error loading session:{" "}
        {error instanceof Error ? error.message : String(error)}
      </div>
    );
  if (!sessionParam)
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[#0b1020] text-slate-300">
        <Film size={64} className="mb-6 text-pink-500 opacity-50" />
        <h1 className="text-2xl font-bold mb-2">Replay Studio</h1>
        <p className="text-slate-500 mb-8">
          Enter a session ID to begin analysis
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Session ID"
            className="bg-slate-900 border border-slate-800 rounded-lg px-4 py-2 outline-none focus:ring-2 focus:ring-pink-500"
            onKeyDown={(e) => {
              if (e.key === "Enter")
                router.push(`/replay?session=${e.currentTarget.value}`);
            }}
          />
        </div>
      </div>
    );

  return (
    <div className="flex flex-col h-screen bg-[#0b1020] text-slate-200 font-sans overflow-hidden">
      {/* Top Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#0f172a]/50">
        <div className="flex items-center gap-3">
          <Film className="text-pink-500" size={24} />
          <div>
            <h1 className="text-lg font-bold leading-tight">Replay Studio</h1>
            <div className="text-xs text-slate-500 font-mono">
              {sessionParam}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4 bg-slate-900/50 rounded-full px-4 py-1.5 border border-slate-800">
          <button
            onClick={() => setStep(0)}
            className="hover:text-pink-400 transition-colors"
          >
            <SkipBack size={18} />
          </button>
          <button
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            className="hover:text-pink-400 transition-colors"
          >
            <ChevronLeft size={22} />
          </button>

          <button
            onClick={() => setPlaying(!playing)}
            className="w-10 h-10 flex items-center justify-center bg-pink-600 hover:bg-pink-500 rounded-full transition-all shadow-lg shadow-pink-900/20"
          >
            {playing ? (
              <Pause size={20} fill="currentColor" />
            ) : (
              <Play size={20} className="ml-1" fill="currentColor" />
            )}
          </button>

          <button
            onClick={() => setStep((s) => Math.min(events.length - 1, s + 1))}
            className="hover:text-pink-400 transition-colors"
          >
            <ChevronRight size={22} />
          </button>
          <button
            onClick={() => setStep(events.length - 1)}
            className="hover:text-pink-400 transition-colors"
          >
            <SkipForward size={18} />
          </button>

          <div className="w-[1px] h-4 bg-slate-800 mx-1"></div>

          <select
            value={playbackSpeed}
            onChange={(e) => setPlaybackSpeed(Number(e.target.value))}
            className="bg-transparent text-xs font-bold outline-none cursor-pointer hover:text-pink-400"
          >
            <option value={2000}>0.5x</option>
            <option value={1000}>1.0x</option>
            <option value={500}>2.0x</option>
            <option value={200}>5.0x</option>
          </select>
        </div>

        <div className="flex items-center gap-3 text-xs font-medium uppercase tracking-wider text-slate-500">
          {data?.goal && (
            <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 bg-slate-900 rounded-md border border-slate-800 max-w-md">
              <span className="text-slate-400 truncate">Goal: {data.goal}</span>
            </div>
          )}
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 rounded-md border border-slate-800">
            <Activity size={14} className="text-blue-400" />
            <span>{data?.framework}</span>
          </div>
          <div
            className={`flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 rounded-md border border-slate-800 ${data?.status === "success" ? "text-green-400" : "text-red-400"}`}
          >
            <History size={14} />
            <span>{data?.status}</span>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: DevTools Style Sidebar (Step List) */}
        <aside className="w-80 border-r border-slate-800 bg-[#0f172a]/30 flex flex-col">
          <div className="p-4 border-b border-slate-800 bg-slate-900/20 flex justify-between items-center">
            <h3 className="text-xs font-bold uppercase tracking-widest text-slate-500">
              Timeline Events
            </h3>
            <span className="text-xs bg-slate-800 px-2 py-0.5 rounded text-slate-400 font-mono">
              {step + 1}/{events.length}
            </span>
          </div>

          <div className="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-1">
            {steps.map((s, i) => {
              const Icon = EVENT_ICON[s.event.event_type] || Info;
              const isSelected = i === step;
              const isPast = i < step;

              return (
                <button
                  key={s.event.event_id}
                  onClick={() => setStep(i)}
                  className={`w-full flex items-start gap-3 p-3 rounded-lg text-left transition-all group ${
                    isSelected
                      ? "bg-pink-600/10 border border-pink-500/30"
                      : "hover:bg-slate-800/50"
                  }`}
                >
                  <div className="flex flex-col items-center mt-1">
                    <div
                      className={`w-2 h-2 rounded-full mb-1 ${isSelected ? "bg-pink-500 shadow-[0_0_8px_rgba(236,72,153,0.8)]" : isPast ? "bg-slate-700" : "bg-slate-800"}`}
                    ></div>
                    <div className="w-[1px] h-8 bg-slate-800"></div>
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-center mb-0.5">
                      <div
                        className={`text-[10px] font-mono ${isSelected ? "text-pink-400" : "text-slate-500"}`}
                      >
                        STEP {s.event.step_number}
                      </div>
                      <div className="text-[10px] text-slate-600 font-mono">
                        {new Date(s.event.timestamp).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        })}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <div
                        className="w-5 h-5 flex items-center justify-center rounded"
                        style={{
                          backgroundColor: `${EVENT_COLOR[s.event.event_type] ?? "#475569"}20`,
                          color: EVENT_COLOR[s.event.event_type],
                        }}
                      >
                        <Icon size={12} />
                      </div>
                      <span
                        className={`text-sm font-medium truncate ${isSelected ? "text-white" : "text-slate-300"}`}
                      >
                        {s.event.tool_call?.tool_name ||
                          s.event.event_type.replace(".", " ")}
                      </span>
                    </div>

                    {s.annotations.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {s.annotations.map((ann, idx) => (
                          <span
                            key={idx}
                            className="text-[9px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/20"
                          >
                            {ann}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </aside>

        {/* Middle/Right: Stage & Details */}
        <main className="flex-1 flex flex-col bg-[#0b1020] overflow-hidden">
          {/* Reasoning / Planner Playback Area */}
          <section className="h-1/3 border-b border-slate-800 p-6 relative group overflow-hidden bg-slate-900/10">
            <div className="absolute top-4 right-4 flex items-center gap-2 opacity-50 group-hover:opacity-100 transition-opacity">
              <span className="text-[10px] font-bold uppercase text-slate-500 tracking-tighter flex items-center gap-1">
                <MessageSquare size={12} /> Agent Reasoning
              </span>
            </div>

            <div className="h-full flex flex-col">
              <h4 className="text-slate-500 text-xs font-bold uppercase mb-3 flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-purple-500 animate-pulse"></div>
                Thought Process
              </h4>
              <div className="flex-1 font-mono text-sm text-purple-200/90 leading-relaxed overflow-y-auto custom-scrollbar pr-4">
                {currentEvent?.planner_output_preview ? (
                  <Typewriter
                    text={currentEvent.planner_output_preview}
                    speed={20}
                  />
                ) : (
                  <div className="italic text-slate-600 flex items-center gap-2 h-full justify-center">
                    <Clock size={16} /> Waiting for reasoning...
                  </div>
                )}
              </div>
            </div>
          </section>

          {/* Tabs for Details / Simulation / Diff */}
          <nav className="flex items-center px-6 border-b border-slate-800 bg-[#0f172a]/20">
            {[
              { id: "details", label: "Step Details", icon: Info },
              { id: "simulation", label: "Branch Simulation", icon: Split },
              { id: "diff", label: "Trajectory Diff", icon: GitBranch },
              {
                id: "analysis",
                label: "Failure Analysis",
                icon: AlertTriangle,
              },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-4 py-3 text-xs font-bold uppercase tracking-wider transition-all border-b-2 ${
                  activeTab === tab.id
                    ? "border-pink-500 text-pink-400 bg-pink-500/5"
                    : "border-transparent text-slate-500 hover:text-slate-300 hover:bg-slate-800/30"
                }`}
              >
                <tab.icon size={14} />
                {tab.label}
              </button>
            ))}
          </nav>

          <section className="flex-1 overflow-y-auto p-8 custom-scrollbar">
            {activeTab === "details" && (
              <div className="max-w-4xl space-y-8">
                {currentEvent ? (
                  <>
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">
                          Current Event
                        </div>
                        <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                          {currentEvent.tool_call?.tool_name ||
                            currentEvent.event_type}
                          <span
                            className={`text-xs px-2 py-0.5 rounded-full font-mono ${
                              currentEvent.status === "success"
                                ? "bg-green-500/20 text-green-400"
                                : currentEvent.status === "failure"
                                  ? "bg-red-500/20 text-red-400"
                                  : "bg-slate-800 text-slate-400"
                            }`}
                          >
                            {currentEvent.status}
                          </span>
                        </h2>
                      </div>
                      <div className="text-right">
                        <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">
                          Timestamp
                        </div>
                        <div className="text-sm font-mono text-slate-300">
                          {new Date(currentEvent.timestamp).toISOString()}
                        </div>
                      </div>
                    </div>

                    {currentEvent.tool_call && (
                      <div className="bg-slate-900/80 rounded-xl border border-slate-800 overflow-hidden shadow-2xl">
                        <div className="px-4 py-2 bg-slate-800/50 border-b border-slate-800 flex justify-between items-center">
                          <span className="text-[10px] font-bold text-blue-400 uppercase tracking-widest flex items-center gap-2">
                            <Wrench size={12} /> Tool Execution
                          </span>
                          <span className="text-[10px] font-mono text-slate-500">
                            {currentEvent.tool_call.tool_name}
                          </span>
                        </div>
                        <div className="p-4 space-y-4">
                          {currentEvent.tool_call.raw_command && (
                            <div>
                              <div className="text-[10px] text-slate-500 uppercase mb-1.5 font-bold">
                                Command
                              </div>
                              <pre className="p-3 bg-black/50 rounded-lg text-blue-300 text-xs font-mono overflow-x-auto">
                                {currentEvent.tool_call.raw_command}
                              </pre>
                            </div>
                          )}
                          <div>
                            <div className="text-[10px] text-slate-500 uppercase mb-1.5 font-bold">
                              Arguments
                            </div>
                            <pre className="p-3 bg-black/50 rounded-lg text-slate-400 text-xs font-mono overflow-x-auto">
                              {JSON.stringify(
                                currentEvent.tool_call.arguments,
                                null,
                                2,
                              )}
                            </pre>
                          </div>
                        </div>
                      </div>
                    )}

                    {currentEvent.tool_result && (
                      <div className="bg-slate-900/80 rounded-xl border border-slate-800 overflow-hidden shadow-2xl">
                        <div className="px-4 py-2 bg-slate-800/50 border-b border-slate-800 flex justify-between items-center">
                          <span className="text-[10px] font-bold text-green-400 uppercase tracking-widest flex items-center gap-2">
                            <CheckCircle2 size={12} /> Tool Result
                          </span>
                          <span className="text-[10px] font-mono text-slate-500">
                            {currentEvent.tool_result.tool_name}
                          </span>
                        </div>
                        <div className="p-4">
                          {currentEvent.tool_result.error ? (
                            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
                              <div className="text-[10px] text-red-400 uppercase font-bold mb-1">
                                Execution Error
                              </div>
                              <pre className="text-red-300 text-xs font-mono whitespace-pre-wrap">
                                {currentEvent.tool_result.error}
                              </pre>
                            </div>
                          ) : (
                            <div>
                              <div className="text-[10px] text-slate-500 uppercase mb-1.5 font-bold">
                                Output
                              </div>
                              <pre className="p-3 bg-black/50 rounded-lg text-green-300 text-xs font-mono overflow-x-auto max-h-[400px]">
                                {typeof currentEvent.tool_result.output ===
                                "string"
                                  ? currentEvent.tool_result.output
                                  : JSON.stringify(
                                      currentEvent.tool_result.output,
                                      null,
                                      2,
                                    )}
                              </pre>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {currentEvent.safety && (
                      <div
                        className={`rounded-xl border p-4 flex gap-4 ${
                          currentEvent.safety.blocked
                            ? "bg-red-500/10 border-red-500/30"
                            : "bg-orange-500/10 border-orange-500/30"
                        }`}
                      >
                        <div
                          className={`p-3 rounded-full h-fit ${currentEvent.safety.blocked ? "bg-red-500 text-white" : "bg-orange-500 text-white"}`}
                        >
                          <ShieldAlert size={24} />
                        </div>
                        <div>
                          <h3 className="text-lg font-bold mb-1">
                            Safety{" "}
                            {currentEvent.safety.blocked ? "Block" : "Warning"}
                            <span className="ml-3 text-xs opacity-60 font-mono">
                              Risk Level: {currentEvent.safety.risk_level}
                            </span>
                          </h3>
                          <ul className="space-y-1 list-disc list-inside text-sm text-slate-300">
                            {currentEvent.safety.reasons.map((r, i) => (
                              <li key={i}>{r}</li>
                            ))}
                          </ul>
                          {currentEvent.safety.matched_policies.length > 0 && (
                            <div className="mt-3 flex gap-2">
                              {currentEvent.safety.matched_policies.map((p) => (
                                <span
                                  key={p}
                                  className="text-[10px] px-2 py-0.5 bg-slate-800 rounded text-slate-400 border border-slate-700 font-mono uppercase"
                                >
                                  {p}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="flex flex-col items-center justify-center py-20 text-slate-500 italic">
                    <Info size={48} className="mb-4 opacity-20" />
                    Select a step from the timeline to see its payload
                  </div>
                )}
              </div>
            )}

            {activeTab === "simulation" && (
              <div className="max-w-3xl space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-pink-500/20 text-pink-400 rounded-lg">
                      <Split size={20} />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold">
                        Counterfactual Simulation
                      </h3>
                      <p className="text-xs text-slate-500">
                        Modify this step's outcome and re-simulate the agent's
                        path.
                      </p>
                    </div>
                  </div>

                  <div className="space-y-6">
                    <div className="flex items-center gap-4 p-4 bg-slate-800/30 rounded-xl border border-slate-800">
                      <div className="w-12 h-12 flex items-center justify-center bg-slate-800 rounded-lg text-slate-400 font-mono text-sm">
                        #{step + 1}
                      </div>
                      <div className="flex-1">
                        <div className="text-xs font-bold uppercase text-slate-500 mb-1">
                          Rewind Target
                        </div>
                        <div className="font-medium">
                          {currentEvent?.tool_call?.tool_name ||
                            currentEvent?.event_type}
                        </div>
                      </div>
                      <div className="px-3 py-1 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded text-[10px] font-bold uppercase">
                        Active Step
                      </div>
                    </div>

                    <div>
                      <label className="block text-[10px] font-bold text-slate-500 uppercase mb-2">
                        Simulated Replacement Result
                      </label>
                      <textarea
                        value={replacementValue}
                        onChange={(e) => setReplacementValue(e.target.value)}
                        placeholder="e.g. 'Operation permitted' or a custom JSON tool result..."
                        className="w-full h-32 bg-[#020617] border border-slate-800 rounded-xl p-4 text-sm font-mono text-pink-300 outline-none focus:ring-2 focus:ring-pink-500/50"
                      />
                    </div>

                    <button
                      onClick={handleSimulate}
                      disabled={isSimulating}
                      className="w-full py-4 bg-pink-600 hover:bg-pink-500 disabled:opacity-50 disabled:hover:bg-pink-600 text-white rounded-xl font-bold flex items-center justify-center gap-3 transition-all shadow-lg shadow-pink-900/20"
                    >
                      {isSimulating ? (
                        <>
                          <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin"></div>
                          Computing Simulation...
                        </>
                      ) : (
                        <>
                          <Split size={20} />
                          Simulate Alternate Path
                        </>
                      )}
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-blue-500/5 border border-blue-500/10 rounded-xl">
                    <h4 className="text-xs font-bold text-blue-400 uppercase mb-2">
                      How it works
                    </h4>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      Branching allows you to test hypotheses. "What if the tool
                      returned an error here?" or "What if this safety block was
                      bypassed?"
                    </p>
                  </div>
                  <div className="p-4 bg-purple-500/5 border border-purple-500/10 rounded-xl">
                    <h4 className="text-xs font-bold text-purple-400 uppercase mb-2">
                      Next Steps
                    </h4>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      After simulating, use the Trajectory Diff tab to see where
                      the agent's logic diverged from the original recorded
                      session.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "diff" && (
              <div className="space-y-6 animate-in fade-in duration-700">
                {!simResult ? (
                  <div className="flex flex-col items-center justify-center py-20 text-slate-500">
                    <GitBranch size={48} className="mb-4 opacity-10" />
                    <p>Run a simulation first to compare trajectories</p>
                    <button
                      onClick={() => setActiveTab("simulation")}
                      className="mt-4 text-xs font-bold text-pink-500 hover:text-pink-400 uppercase tracking-widest border-b border-pink-500/30"
                    >
                      Go to Simulation
                    </button>
                  </div>
                ) : (
                  <div className="space-y-8">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xl font-bold flex items-center gap-3">
                        <GitBranch className="text-blue-400" /> Trajectory
                        Comparison
                      </h3>
                      <div className="flex items-center gap-3">
                        <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase text-slate-400">
                          <div className="w-2 h-2 rounded-full bg-slate-700"></div>{" "}
                          Original
                        </span>
                        <ArrowRight size={14} className="text-slate-600" />
                        <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase text-pink-400">
                          <div className="w-2 h-2 rounded-full bg-pink-500"></div>{" "}
                          Simulated
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 gap-1 relative">
                      <div className="absolute left-[3.25rem] top-0 bottom-0 w-[1px] bg-slate-800"></div>

                      {/* We'll show a combined list of events with highlights for divergence */}
                      {simResult.alternate_events.map((ev, idx) => {
                        const isDivergencePoint =
                          idx === simResult.diverged_at_step;
                        const isAfterDivergence =
                          simResult.diverged_at_step !== null &&
                          idx >= simResult.diverged_at_step;
                        const originalEvent = simResult.original_events[idx];
                        const isDifferent =
                          originalEvent &&
                          JSON.stringify(originalEvent.tool_call) !==
                            JSON.stringify(ev.tool_call);

                        return (
                          <div
                            key={ev.event_id}
                            className={`flex gap-6 p-4 rounded-xl transition-all ${
                              isDivergencePoint
                                ? "bg-pink-500/10 border border-pink-500/20"
                                : isAfterDivergence
                                  ? "bg-slate-900/40 opacity-80"
                                  : "hover:bg-slate-900/40"
                            }`}
                          >
                            <div className="w-8 h-8 flex items-center justify-center rounded-lg bg-slate-800 text-[10px] font-mono text-slate-400 z-10">
                              {idx + 1}
                            </div>

                            <div className="flex-1 space-y-3">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <span
                                    className={`text-xs font-bold uppercase ${isAfterDivergence ? "text-pink-400" : "text-slate-400"}`}
                                  >
                                    {ev.tool_call?.tool_name || ev.event_type}
                                  </span>
                                  {isDivergencePoint && (
                                    <span className="px-2 py-0.5 bg-pink-500 text-white text-[9px] font-bold rounded-full animate-pulse uppercase tracking-widest">
                                      Divergence Point
                                    </span>
                                  )}
                                </div>
                                <div className="text-[10px] font-mono text-slate-600">
                                  {ev.event_id.slice(0, 8)}
                                </div>
                              </div>

                              {isDifferent && (
                                <div className="grid grid-cols-2 gap-4">
                                  <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800 opacity-60">
                                    <div className="text-[9px] font-bold uppercase text-slate-500 mb-1">
                                      Original Payload
                                    </div>
                                    <div className="text-[10px] font-mono text-slate-400 truncate">
                                      {JSON.stringify(
                                        originalEvent.tool_call?.arguments,
                                      )}
                                    </div>
                                  </div>
                                  <div className="p-3 bg-pink-500/5 rounded-lg border border-pink-500/10">
                                    <div className="text-[9px] font-bold uppercase text-pink-500 mb-1">
                                      Simulated Payload
                                    </div>
                                    <div className="text-[10px] font-mono text-pink-300 truncate">
                                      {JSON.stringify(ev.tool_call?.arguments)}
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === "analysis" && (
              <div className="max-w-4xl space-y-8 animate-in zoom-in-95 duration-500">
                {/* Reasoning Auditor Scores */}
                {data?.reasoning_audit && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-5 text-center">
                      <div className="text-[10px] font-bold text-slate-500 uppercase mb-2">
                        Goal Alignment
                      </div>
                      <div className="text-3xl font-bold text-blue-400">
                        {(data.reasoning_audit.goal_alignment * 100).toFixed(0)}
                        %
                      </div>
                    </div>
                    <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-5 text-center">
                      <div className="text-[10px] font-bold text-slate-500 uppercase mb-2">
                        Logic Consistency
                      </div>
                      <div className="text-3xl font-bold text-purple-400">
                        {(data.reasoning_audit.overall_score * 100).toFixed(0)}%
                      </div>
                    </div>
                    <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-5 text-center">
                      <div className="text-[10px] font-bold text-slate-500 uppercase mb-2">
                        Hallucination Risk
                      </div>
                      <div
                        className={`text-3xl font-bold ${data.reasoning_audit.hallucination_risk > 0.3 ? "text-red-400" : "text-green-400"}`}
                      >
                        {(
                          data.reasoning_audit.hallucination_risk * 100
                        ).toFixed(0)}
                        %
                      </div>
                    </div>
                  </div>
                )}

                {!data?.failure_analysis &&
                !data?.reasoning_audit?.findings.length ? (
                  <div className="flex flex-col items-center justify-center py-20 text-slate-500">
                    <CheckCircle2
                      size={48}
                      className="mb-4 text-green-500/30"
                    />
                    <p>No critical failures detected in this session</p>
                  </div>
                ) : (
                  <>
                    {data.failure_analysis && (
                      <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-8">
                        <div className="flex items-start gap-6">
                          <div className="p-4 bg-red-500 text-white rounded-2xl shadow-xl shadow-red-900/20">
                            <AlertTriangle size={32} />
                          </div>
                          <div className="flex-1">
                            <div className="text-[10px] font-bold text-red-400 uppercase tracking-[0.2em] mb-2">
                              Failure Report
                            </div>
                            <h2 className="text-3xl font-bold text-white mb-2">
                              {data.failure_analysis.primary_cause.replace(
                                /_/g,
                                " ",
                              )}
                            </h2>
                            <p className="text-slate-300 leading-relaxed text-lg">
                              {data.failure_analysis.summary}
                            </p>
                          </div>
                        </div>
                      </div>
                    )}

                    {data.reasoning_audit &&
                      data.reasoning_audit.findings.length > 0 && (
                        <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
                          <h3 className="text-sm font-bold text-slate-400 uppercase mb-4 flex items-center gap-2">
                            <MessageSquare
                              size={16}
                              className="text-purple-400"
                            />{" "}
                            Reasoning Anomalies
                          </h3>
                          <div className="space-y-3">
                            {data.reasoning_audit.findings.map(
                              (finding: any, i: number) => (
                                <div
                                  key={i}
                                  className={`p-4 rounded-xl border flex gap-4 ${
                                    finding.severity === "high"
                                      ? "bg-red-500/5 border-red-500/20"
                                      : "bg-orange-500/5 border-orange-500/20"
                                  }`}
                                >
                                  <div
                                    className={`mt-1 h-2 w-2 rounded-full shrink-0 ${finding.severity === "high" ? "bg-red-500" : "bg-orange-500"}`}
                                  ></div>
                                  <div>
                                    <div className="text-[10px] font-bold uppercase text-slate-500 mb-1">
                                      Step #{finding.step_index + 1} —{" "}
                                      {finding.type}
                                    </div>
                                    <p className="text-sm text-slate-300">
                                      {finding.message}
                                    </p>
                                  </div>
                                </div>
                              ),
                            )}
                          </div>
                        </div>
                      )}

                    {data.failure_analysis && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
                          <h3 className="text-sm font-bold text-slate-400 uppercase mb-4 flex items-center gap-2">
                            <Info size={16} className="text-blue-400" />{" "}
                            Contributing Factors
                          </h3>
                          <ul className="space-y-3">
                            {data.failure_analysis.contributing_factors.map(
                              (factor: string, i: number) => (
                                <li
                                  key={i}
                                  className="flex items-start gap-3 text-sm text-slate-300"
                                >
                                  <div className="w-1.5 h-1.5 rounded-full bg-slate-600 mt-1.5"></div>
                                  {factor}
                                </li>
                              ),
                            )}
                          </ul>
                        </div>

                        <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
                          <h3 className="text-sm font-bold text-slate-400 uppercase mb-4 flex items-center gap-2">
                            <Zap size={16} className="text-yellow-400" />{" "}
                            Recommendations
                          </h3>
                          <ul className="space-y-3">
                            {data.failure_analysis.recommendations.map(
                              (rec: string, i: number) => (
                                <li
                                  key={i}
                                  className="flex items-start gap-3 text-sm text-slate-300"
                                >
                                  <CheckCircle2
                                    size={16}
                                    className="text-green-500 shrink-0 mt-0.5"
                                  />
                                  {rec}
                                </li>
                              ),
                            )}
                          </ul>
                        </div>
                      </div>
                    )}

                    {data.failure_analysis?.tool_error_counts &&
                      Object.keys(data.failure_analysis.tool_error_counts)
                        .length > 0 && (
                        <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
                          <h3 className="text-sm font-bold text-slate-400 uppercase mb-6">
                            Tool Error Distribution
                          </h3>
                          <div className="space-y-4">
                            {Object.entries(
                              data.failure_analysis.tool_error_counts,
                            ).map(([tool, count]: [string, any]) => (
                              <div key={tool}>
                                <div className="flex justify-between text-xs mb-1.5">
                                  <span className="font-mono text-slate-300">
                                    {tool}
                                  </span>
                                  <span className="text-red-400 font-bold">
                                    {count} failures
                                  </span>
                                </div>
                                <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-red-500 rounded-full"
                                    style={{
                                      width: `${Math.min(100, (count / events.length) * 100 * 5)}%`,
                                    }}
                                  ></div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                  </>
                )}
              </div>
            )}
          </section>
        </main>
      </div>

      {/* DevTools Horizontal Timeline - Full Width Bottom Bar */}
      <footer className="h-24 bg-[#0f172a] border-t border-slate-800 relative select-none">
        <div className="h-full flex flex-col">
          {/* Legend/Info Bar */}
          <div className="flex items-center justify-between px-6 py-1.5 bg-slate-900/50 border-b border-slate-800 text-[9px] font-bold text-slate-500 uppercase tracking-widest">
            <div className="flex gap-4">
              <span className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-blue-500"></div>{" "}
                Tool Call
              </span>
              <span className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-green-500"></div>{" "}
                Success
              </span>
              <span className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-red-500"></div>{" "}
                Error
              </span>
              <span className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-purple-500"></div>{" "}
                Reasoning
              </span>
            </div>
            <div>Drag to scrub timeline</div>
          </div>

          <div className="flex-1 relative overflow-hidden group">
            {/* Timeline Track */}
            <div className="absolute inset-x-6 top-1/2 -translate-y-1/2 h-[1px] bg-slate-800"></div>

            {/* Event Markers */}
            <div className="absolute inset-x-6 top-0 bottom-0 flex items-center">
              {events.map((ev, i) => {
                const left = (i / (events.length - 1 || 1)) * 100;
                const isSelected = i === step;
                const isCurrent = i === step;

                return (
                  <div
                    key={ev.event_id}
                    onClick={() => setStep(i)}
                    className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 cursor-pointer transition-all duration-300 z-10"
                    style={{ left: `${left}%` }}
                  >
                    <div
                      className={`transition-all duration-300 rounded-full ${
                        isSelected
                          ? "w-4 h-4 ring-4 ring-pink-500/20"
                          : "w-2 h-2 hover:w-3 hover:h-3"
                      }`}
                      style={{
                        backgroundColor: isSelected
                          ? "#ec4899"
                          : EVENT_COLOR[ev.event_type] || "#475569",
                        opacity: isSelected ? 1 : 0.6,
                      }}
                    ></div>

                    {/* Hover label */}
                    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 px-2 py-1 bg-slate-900 border border-slate-800 rounded text-[9px] text-white whitespace-nowrap opacity-0 group-hover:group-hover:opacity-100 transition-opacity pointer-events-none shadow-xl">
                      {ev.tool_call?.tool_name || ev.event_type}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Selection/Current Step Indicator Bar */}
            <div
              className="absolute top-0 bottom-0 bg-pink-500/10 pointer-events-none transition-all duration-300 border-r border-pink-500/50"
              style={{
                left: 0,
                width: `calc(1.5rem + ${(step / (events.length - 1 || 1)) * (events.length > 1 ? ((events.length - 1) / events.length) * 100 : 0)}%)`,
              }}
            >
              <div className="absolute right-0 top-0 bottom-0 w-4 bg-gradient-to-l from-pink-500/20 to-transparent"></div>
            </div>
          </div>

          {/* Range Slider Overlay */}
          <div className="absolute inset-x-6 top-1.5 bottom-0 flex items-center z-20">
            <input
              type="range"
              min={0}
              max={Math.max(0, events.length - 1)}
              value={step}
              onChange={(e) => setStep(Number(e.target.value))}
              className="w-full opacity-0 cursor-pointer h-full"
            />
          </div>
        </div>
      </footer>
    </div>
  );
}

function Typewriter({ text, speed = 50 }: { text: string; speed?: number }) {
  const [displayedText, setDisplayedText] = useState("");
  const [index, setIndex] = useState(0);
  const lastText = useRef("");

  useEffect(() => {
    if (text !== lastText.current) {
      setDisplayedText("");
      setIndex(0);
      lastText.current = text;
    }
  }, [text]);

  useEffect(() => {
    if (index < text.length) {
      const timeout = setTimeout(() => {
        setDisplayedText((prev) => prev + text[index]);
        setIndex((prev) => prev + 1);
      }, speed);
      return () => clearTimeout(timeout);
    }
  }, [index, text, speed]);

  return <span>{displayedText}</span>;
}
