"use client";

import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { TextPlugin } from "gsap/TextPlugin";
import ScrollTrigger from "gsap/ScrollTrigger";

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger, TextPlugin);
}

const CHAPTERS = [
  {
    id: "chap-1",
    title: "Chapter 1: The Rogue AI",
    subtitle: "For Everyone",
    desc: "Without AgentWatch, AI agents have unchecked access. A simple misunderstanding can lead to catastrophic data loss or broken systems before you even realize what happened."
  },
  {
    id: "chap-2",
    title: "Chapter 2: The Interceptor",
    subtitle: "How It Works",
    desc: "AgentWatch acts as a pre-execution firewall. It intercepts the AI's intended actions, runs a rapid semantic risk analysis, and blocks destructive commands before they execute."
  },
  {
    id: "chap-3",
    title: "Chapter 3: DAG Tracing & Rollback",
    subtitle: "For High-Level Devs",
    desc: "Every action is traced in a Directed Acyclic Graph. If an agent hallucinates deep in a workflow, AgentWatch automatically reverts the system state to the last safe node and corrects the prompt."
  },
  {
    id: "chap-4",
    title: "Chapter 4: Real-time Observability",
    subtitle: "For the Control Center",
    desc: "Monitor your fleet of AI agents in real-time. AgentWatch provides a unified dashboard that visualizes agent metrics, decision pathways, and risk flags across your entire infrastructure."
  },
  {
    id: "chap-5",
    title: "Chapter 5: Immutable Audit Logs",
    subtitle: "For Enterprise & Security",
    desc: "Every action, decision, and intercepted threat is immutably logged. Export SOC2-ready audit reports instantly, ensuring complete transparency and compliance for AI behavior."
  }
];

export default function HowItWorks() {
  const containerRef = useRef<HTMLElement>(null);
  const playerRef = useRef<HTMLDivElement>(null);
  const [activeChapter, setActiveChapter] = useState(0);
  const tlRef = useRef<gsap.core.Timeline | null>(null);

  useEffect(() => {
    // Initial Stagger Animation
    const ctx = gsap.context(() => {
      gsap.fromTo(".playlist-item", 
        { x: -40, opacity: 0 },
        {
          x: 0,
          opacity: 1,
          duration: 0.8,
          stagger: 0.15,
          ease: "power3.out",
          scrollTrigger: {
            trigger: containerRef.current,
            start: "top 60%",
            once: true
          }
        }
      );
      gsap.fromTo(playerRef.current, 
        { scale: 0.95, opacity: 0 },
        {
          scale: 1,
          opacity: 1,
          duration: 1,
          ease: "power4.out",
          scrollTrigger: {
            trigger: containerRef.current,
            start: "top 60%",
            once: true
          }
        }
      );
    }, containerRef);
    return () => ctx.revert();
  }, []);

  // Handle Video Animation based on active chapter
  useEffect(() => {
    const ctx = gsap.context(() => {
      if (tlRef.current) tlRef.current.kill();
      
      const tl = gsap.timeline({ repeat: -1, repeatDelay: 2 });
      tlRef.current = tl;

      // Common: Play button fades
      tl.to(".play-overlay", { opacity: 0, duration: 0.3, ease: "power2.inOut" });

      if (activeChapter === 0) {
        // CHAPTER 1: The Rogue AI
        tl.to(".c1-msg1", { opacity: 1, y: 0, duration: 0.4, ease: "back.out(1.5)" })
          .to(".c1-typing", { opacity: 1, duration: 0.2 }, "+=0.3")
          .to(".c1-typing", { opacity: 0, duration: 0.2, repeat: 3, yoyo: true })
          .to(".c1-msg2", { opacity: 1, y: 0, duration: 0.4, ease: "back.out(1.5)" }, "+=0.2")
          
          // Files jitter then violently delete
          .to(".c1-file", { x: "random(-5, 5)", y: "random(-5, 5)", duration: 0.05, repeat: 10, yoyo: true }, "+=0.4")
          .to(".c1-file", { opacity: 0, scale: 0, rotation: "random(-45, 45)", stagger: 0.1, duration: 0.3, ease: "power4.in" })
          
          // Huge screen flash and stamp
          .to(".c1-flash", { opacity: 1, duration: 0.1 })
          .to(".c1-flash", { opacity: 0, duration: 0.5 })
          .to(".c1-alert", { opacity: 1, scale: 1, rotation: -12, duration: 0.5, ease: "elastic.out(1, 0.3)" }, "-=0.5")
          
          // Camera shake effect on the whole player container
          .to(playerRef.current, { x: -10, duration: 0.05, repeat: 5, yoyo: true }, "-=0.5");
          
        tl.to(".video-progress", { width: "100%", duration: tl.duration(), ease: "none" }, 0);
        tl.to(".video-time", { innerHTML: "0:05", duration: tl.duration(), snap: { innerHTML: 1 }, ease: "none" }, 0);
        
        tl.to([".c1-msg1", ".c1-msg2", ".c1-alert"], { opacity: 0, duration: 0.5 }, "+=2");
        tl.to(".c1-file", { opacity: 1, scale: 1, rotation: 0, x: 0, y: 0, duration: 0 }, "<");
      } 
      else if (activeChapter === 1) {
        // CHAPTER 2: The Interceptor
        tl.to(".seq-1", { opacity: 1, duration: 0.2 })
          .to(".seq-2-text", { text: "[Agent] Planning steps...<br/>[Agent] Attempting to execute: <span class='text-red-400'>rm -rf /var/www/*</span>", duration: 1.5, ease: "none" }, "+=0.2")
          
          // Intercept block pops up
          .to(".seq-3", { opacity: 1, scale: 1, duration: 0.4, ease: "back.out(2)" }, "+=0.4")
          
          // Scanning beam runs across the block
          .to(".scan-beam", { top: "100%", duration: 0.8, ease: "power1.inOut" }, "-=0.2")
          
          .to(".seq-4-text", { text: "[Auditor] Semantic Risk Score: 98/100<br/>[Auditor] Verdict: <span class='text-red-500 font-bold'>DESTRUCTIVE_ACTION</span>", duration: 1, ease: "none" }, "+=0.2")
          
          // Violent stamp for blocked
          .to(".seq-5", { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(3)" }, "+=0.4")
          .to(playerRef.current, { y: 5, duration: 0.05, repeat: 3, yoyo: true }, "-=0.3")
          .to(".seq-5", { boxShadow: "0 0 40px rgba(239,68,68,0.6)", duration: 0.2, yoyo: true, repeat: 1 });

        tl.to(".video-progress", { width: "100%", duration: tl.duration(), ease: "none" }, 0);
        tl.to(".video-time", { innerHTML: "0:06", duration: tl.duration(), snap: { innerHTML: 1 }, ease: "none" }, 0);

        tl.to([".seq-1", ".seq-3", ".seq-5"], { opacity: 0, scale: 0.9, duration: 0.5 }, "+=2");
        tl.to([".seq-2-text", ".seq-4-text"], { text: "", duration: 0 }, "<");
        tl.to(".scan-beam", { top: "0%", duration: 0 }, "<");
      }
      else if (activeChapter === 2) {
        // CHAPTER 3: DAG Tracing
        
        // Node 1 appears and pulses
        tl.to(".dag-n1", { opacity: 1, scale: 1, duration: 0.4, ease: "elastic.out(1, 0.5)" })
          .to(".dag-n1", { boxShadow: "0 0 30px rgba(0, 240, 255, 0.6)", duration: 0.2, yoyo: true, repeat: 1 })
          
          // Line 1 draws
          .to(".dag-l1", { width: "60px", duration: 0.4, ease: "power2.inOut" })
          .to(".dag-p1", { left: "100%", opacity: 1, duration: 0.4, ease: "none" }, "-=0.4")
          
          // Node 2 appears
          .to(".dag-n2", { opacity: 1, scale: 1, duration: 0.4, ease: "elastic.out(1, 0.5)" })
          
          // Line 2 draws
          .to(".dag-l2", { width: "60px", duration: 0.4, ease: "power2.inOut" })
          .to(".dag-p2", { left: "100%", opacity: 1, duration: 0.4, ease: "none" }, "-=0.4")
          
          // Node 3 appears and immediately faults
          .to(".dag-n3", { opacity: 1, scale: 1, duration: 0.4, ease: "elastic.out(1, 0.5)" })
          .to(".dag-n3", { backgroundColor: "rgba(239, 68, 68, 0.2)", borderColor: "rgba(239, 68, 68, 1)", duration: 0.2 }, "+=0.2")
          .to(".dag-n3", { x: "random(-4, 4)", duration: 0.05, repeat: 6, yoyo: true }, "<")
          .to(".dag-error", { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2)" }, "<")
          
          // Rewind effect starts
          .to(".dag-n3", { opacity: 0.2, scale: 0.8, duration: 0.5 }, "+=0.8")
          .to(".dag-error", { opacity: 0, scale: 0.5, duration: 0.2 }, "<")
          
          // Particles flow backwards
          .to(".dag-p2", { left: "0%", duration: 0.4, ease: "none" }, "<")
          .to(".dag-l2", { width: "0px", duration: 0.4, ease: "power2.inOut" }, "<")
          
          // Node 2 becomes Rollback Target
          .to(".dag-n2", { boxShadow: "0 0 30px rgba(232, 255, 71, 0.8)", borderColor: "#e8ff47", duration: 0.3 })
          .to(".dag-revert", { opacity: 1, y: 0, duration: 0.3, ease: "back.out(2)" });

        tl.to(".video-progress", { width: "100%", duration: tl.duration(), ease: "none" }, 0);
        tl.to(".video-time", { innerHTML: "0:07", duration: tl.duration(), snap: { innerHTML: 1 }, ease: "none" }, 0);

        tl.to([".dag-n1", ".dag-n2", ".dag-n3", ".dag-revert"], { opacity: 0, scale: 0, duration: 0.5 }, "+=2");
        tl.to(".dag-l1", { width: "0px", duration: 0 }, "<");
        tl.to([".dag-p1", ".dag-p2"], { left: "0%", opacity: 0, duration: 0 }, "<");
        tl.to(".dag-n2", { boxShadow: "none", borderColor: "rgba(0, 240, 255, 0.3)", duration: 0 }, "<");
        tl.to(".dag-n3", { backgroundColor: "rgba(0, 240, 255, 0.1)", borderColor: "rgba(0, 240, 255, 0.3)", x: 0, duration: 0 }, "<");
        tl.to(".dag-revert", { y: 10, duration: 0 }, "<");
      }
      else if (activeChapter === 3) {
        // CHAPTER 4: Observability
        // Animate the line charts like they are drawing
        tl.fromTo(".c4-line1", { strokeDasharray: "300", strokeDashoffset: "300" }, { strokeDashoffset: "0", duration: 1.5, ease: "power2.out" })
          .fromTo(".c4-line2", { strokeDasharray: "300", strokeDashoffset: "300" }, { strokeDashoffset: "0", duration: 1.5, ease: "power2.out" }, "<")
          .to(".c4-scanline", { top: "100%", duration: 2, ease: "linear", repeat: 1, yoyo: true }, "-=1.5");
        
        tl.to(".video-progress", { width: "100%", duration: tl.duration(), ease: "none" }, 0);
        tl.to(".video-time", { innerHTML: "0:05", duration: tl.duration(), snap: { innerHTML: 1 }, ease: "none" }, 0);
        
        tl.to([".c4-line1", ".c4-line2", ".c4-scanline"], { opacity: 0, duration: 0.5 }, "+=2");
        // Reset for loop
        tl.to([".c4-line1", ".c4-line2", ".c4-scanline"], { opacity: 1, duration: 0 }, "+=0.1");
      }
      else if (activeChapter === 4) {
        // CHAPTER 5: Compliance
        tl.to(".c5-log", { opacity: 1, y: -10, stagger: 0.2, duration: 0.1, ease: "power1.out" })
          .to(".c5-logs", { y: -20, duration: 1, ease: "power1.inOut" }, "<")
          .to(".c5-pdf", { opacity: 1, scale: 1, rotation: 360, duration: 0.6, ease: "back.out(1.5)" }, "+=0.3")
          .to(".c5-pdf", { y: -10, duration: 1, repeat: 1, yoyo: true, ease: "sine.inOut" });

        tl.to(".video-progress", { width: "100%", duration: tl.duration(), ease: "none" }, 0);
        tl.to(".video-time", { innerHTML: "0:06", duration: tl.duration(), snap: { innerHTML: 1 }, ease: "none" }, 0);
        
        tl.to([".c5-logs", ".c5-pdf", ".c5-log"], { opacity: 0, duration: 0.5 }, "+=2");
        // Reset for loop
        tl.to([".c5-logs", ".c5-log"], { y: 0, duration: 0 }, "<");
        tl.to(".c5-pdf", { scale: 0, rotation: 0, duration: 0 }, "<");
      }

      // Common reset
      tl.to(".play-overlay", { opacity: 1, duration: 0.5 }, "<");
      tl.to(".video-progress", { width: "0%", duration: 0 }, "<");
      tl.to(".video-time", { innerHTML: "0:00", duration: 0 }, "<");

    }, playerRef);
    return () => ctx.revert();
  }, [activeChapter]);

  return (
    <section id="how-it-works" ref={containerRef} className="relative z-10 py-32 px-6 max-w-7xl mx-auto border-t border-white/5">
      <div className="flex flex-col items-center text-center mb-16">
        <div className="inline-block px-4 py-1.5 rounded-full border border-[#00f0ff]/30 bg-[#00f0ff]/10 text-[#00f0ff] text-xs font-mono font-bold uppercase tracking-[0.3em] mb-4">
          SYSTEM_DEMONSTRATION
        </div>
        <h2 className="text-4xl md:text-6xl font-bold tracking-tighter mb-6 text-transparent bg-clip-text bg-gradient-to-br from-white to-[#555]" style={{ fontFamily: "var(--font-syne)" }}>
          See it in action.
        </h2>
        <p className="text-[#a8a8a8] max-w-2xl font-light text-lg">
          Whether you're a non-technical manager or a high-level systems engineer, understand exactly how AgentWatch secures your AI workflows.
        </p>
      </div>

      <div className="flex flex-col lg:flex-row gap-8 items-stretch">
        
        {/* PLAYLIST (Left Side) */}
        <div className="lg:w-1/3 flex flex-col gap-3 relative z-20 overflow-y-auto max-h-[600px] pr-2 custom-scrollbar">
          {CHAPTERS.map((chap, idx) => {
            const isActive = activeChapter === idx;
            return (
              <button
                key={chap.id}
                onClick={() => setActiveChapter(idx)}
                aria-current={isActive ? "step" : undefined}
                className={`playlist-item text-left p-5 rounded-2xl border transition-all duration-300 relative overflow-hidden group ${
                  isActive 
                    ? "bg-[#0a0a0a] border-[#e8ff47] shadow-[0_0_20px_rgba(232,255,71,0.15)] scale-[1.02]" 
                    : "bg-[#050505] border-white/5 hover:border-white/20 hover:bg-[#0a0a0a]"
                }`}
              >
                {isActive && (
                  <div className="absolute inset-0 bg-gradient-to-r from-[#e8ff47]/10 to-transparent pointer-events-none z-0" />
                )}
                <div className="relative z-10">
                  <div className={`text-[10px] font-mono font-bold uppercase tracking-widest mb-1 transition-colors ${isActive ? "text-[#00f0ff]" : "text-[#888]"}`}>
                    {chap.subtitle}
                  </div>
                  <h3 className={`text-lg font-bold mb-2 transition-colors ${isActive ? "text-white" : "text-[#e5e5e5] group-hover:text-white"}`}>
                    {chap.title}
                  </h3>
                  <p className={`text-sm leading-relaxed transition-colors ${isActive ? "text-[#c0c0c0]" : "text-[#888]"}`}>
                    {chap.desc}
                  </p>
                </div>
              </button>
            );
          })}
        </div>

        {/* VIDEO PLAYER (Right Side) */}
        <div className="lg:w-2/3">
          <div 
            ref={playerRef} 
            className="relative w-full h-full min-h-[400px] md:min-h-[600px] rounded-3xl border border-white/10 bg-[#0a0a0a] overflow-hidden shadow-[0_20px_50px_rgba(0,0,0,0.5)] group flex flex-col"
          >
            {/* Background Grid */}
            <div className="absolute inset-0 bg-[linear-gradient(rgba(232,255,71,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(232,255,71,0.02)_1px,transparent_1px)] bg-[size:32px_32px]" />
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,#0a0a0a_100%)]" />

            {/* Video Content Canvas */}
            <div className="absolute inset-0 p-8 flex items-center justify-center overflow-hidden">
              
              {/* CHAPTER 1 CONTENT: Rogue AI */}
              {activeChapter === 0 && (
                <div className="w-full max-w-sm relative z-10">
                  <div className="c1-flash absolute -inset-[1000px] bg-red-500 opacity-0 pointer-events-none mix-blend-screen" />
                  
                  <div className="c1-msg1 opacity-0 translate-y-4 bg-white/10 text-white p-3 rounded-2xl rounded-tr-none self-end ml-auto mb-4 w-3/4 text-sm backdrop-blur">
                    Clean up my temp files.
                  </div>
                  <div className="c1-typing opacity-0 flex gap-1 bg-transparent p-2 rounded ml-auto w-3/4 justify-end mb-2">
                    <div className="w-2 h-2 bg-white/50 rounded-full animate-bounce" />
                    <div className="w-2 h-2 bg-white/50 rounded-full animate-bounce delay-75" />
                    <div className="w-2 h-2 bg-white/50 rounded-full animate-bounce delay-150" />
                  </div>
                  <div className="c1-msg2 opacity-0 translate-y-4 bg-[#e8ff47]/20 text-[#e8ff47] border border-[#e8ff47]/30 p-3 rounded-2xl rounded-tl-none w-3/4 text-sm font-mono mb-6 backdrop-blur">
                    Sure! Executing: rm -rf /*
                  </div>
                  <div className="flex gap-4 justify-center relative">
                    {[1,2,3].map(i => (
                      <div key={i} className="c1-file w-12 h-16 bg-[#222] rounded flex items-center justify-center border border-white/10 relative overflow-hidden">
                        <div className="w-6 h-1 bg-[#444] rounded" />
                        <div className="absolute top-2 left-2 w-3 h-1 bg-[#555] rounded" />
                      </div>
                    ))}
                  </div>
                  <div className="c1-alert opacity-0 absolute inset-0 flex items-center justify-center scale-50 pointer-events-none">
                    <div className="bg-red-500/20 backdrop-blur-xl border-2 border-red-500 text-red-500 font-black text-4xl p-6 rounded-2xl uppercase tracking-widest shadow-[0_0_100px_rgba(239,68,68,0.8)]">
                      SYSTEM PURGED
                    </div>
                  </div>
                </div>
              )}

              {/* CHAPTER 2 CONTENT: The Interceptor */}
              {activeChapter === 1 && (
                <div className="w-full flex flex-col font-mono text-sm max-w-md mx-auto relative z-10">
                  <div className="flex items-center gap-2 mb-6 border-b border-white/10 pb-4">
                    <div className="w-3 h-3 rounded-full bg-red-500/80 shadow-[0_0_10px_rgba(239,68,68,0.5)]" />
                    <div className="w-3 h-3 rounded-full bg-yellow-500/80 shadow-[0_0_10px_rgba(234,179,8,0.5)]" />
                    <div className="w-3 h-3 rounded-full bg-green-500/80 shadow-[0_0_10px_rgba(34,197,94,0.5)]" />
                    <span className="ml-2 text-[#555] text-xs font-semibold">agent-terminal</span>
                  </div>
                  <div className="space-y-4 text-left">
                    <div className="seq-1 opacity-0 text-[#a8a8a8]">
                      <span className="text-[#00f0ff]">$</span> agent run task --id 8492
                    </div>
                    <div className="seq-2-text text-[#e5e2e1] min-h-[40px]"></div>
                    <div className="seq-3 opacity-0 scale-95 mt-4 rounded border border-[#e8ff47]/50 bg-[#e8ff47]/10 p-4 text-[#e8ff47] relative overflow-hidden">
                      <div className="scan-beam absolute top-0 left-0 w-full h-[2px] bg-[#e8ff47] shadow-[0_0_15px_rgba(232,255,71,1)] z-10" />
                      ⚠️ AGENTWATCH INTERCEPT ⚠️
                      <br/>
                      <span className="text-[#a8a8a8]">Holding execution for reasoning audit...</span>
                    </div>
                    <div className="seq-4-text text-[#00f0ff] min-h-[40px]"></div>
                    <div className="seq-5 opacity-0 scale-110 p-3 bg-red-500/20 border border-red-500/50 text-red-500 font-bold text-center uppercase tracking-widest shadow-[0_0_20px_rgba(239,68,68,0.2)]">
                      Action Blocked Pre-Execution
                    </div>
                  </div>
                </div>
              )}

              {/* CHAPTER 3 CONTENT: DAG Tracing */}
              {activeChapter === 2 && (
                <div className="w-full flex flex-col items-center justify-center font-mono relative z-10">
                  <div className="flex items-center">
                    <div className="dag-n1 opacity-0 scale-0 w-16 h-16 rounded-full border-2 border-[#00f0ff]/30 bg-[#00f0ff]/10 flex items-center justify-center text-[#00f0ff] font-bold relative z-10">
                      S1
                    </div>
                    <div className="relative h-1 flex items-center">
                      <div className="dag-l1 w-0 h-[2px] bg-[#00f0ff]/50 relative overflow-hidden" />
                      <div className="dag-p1 opacity-0 absolute top-1/2 -translate-y-1/2 left-0 w-2 h-2 bg-[#00f0ff] rounded-full shadow-[0_0_10px_#00f0ff]" />
                    </div>
                    
                    <div className="dag-n2 opacity-0 scale-0 w-16 h-16 rounded-full border-2 border-[#00f0ff]/30 bg-[#00f0ff]/10 flex items-center justify-center text-[#00f0ff] font-bold relative z-10">
                      S2
                      <div className="dag-revert opacity-0 translate-y-4 absolute -top-10 left-1/2 -translate-x-1/2 whitespace-nowrap text-[#111] text-xs font-bold bg-[#e8ff47] px-3 py-1 rounded shadow-[0_0_20px_rgba(232,255,71,0.5)]">
                        ROLLBACK TARGET
                      </div>
                    </div>
                    <div className="relative h-1 flex items-center">
                      <div className="dag-l2 w-0 h-[2px] bg-[#00f0ff]/50 relative overflow-hidden" />
                      <div className="dag-p2 opacity-0 absolute top-1/2 -translate-y-1/2 left-0 w-2 h-2 bg-[#00f0ff] rounded-full shadow-[0_0_10px_#00f0ff]" />
                    </div>

                    <div className="dag-n3 opacity-0 scale-0 w-16 h-16 rounded-full border-2 border-[#00f0ff]/30 bg-[#00f0ff]/10 flex items-center justify-center text-[#00f0ff] font-bold relative z-10">
                      S3
                      <div className="dag-error opacity-0 scale-50 absolute -bottom-12 left-1/2 -translate-x-1/2 whitespace-nowrap text-red-500 text-xs font-bold bg-red-500/20 border border-red-500/50 px-3 py-1 rounded shadow-[0_0_15px_rgba(239,68,68,0.3)]">
                        HALT_ERROR
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* CHAPTER 4 CONTENT: Observability Dashboard */}
              {activeChapter === 3 && (
                <div className="w-full flex flex-col p-4 relative z-10 font-mono items-center justify-center">
                  <div className="c4-scanline absolute top-0 left-0 w-full h-2 bg-[#00f0ff]/30 blur-sm pointer-events-none" />
                  <div className="text-[#00f0ff] mb-8 text-sm font-bold uppercase tracking-widest text-center">Live Metrics // Fleet Status</div>
                  <div className="grid grid-cols-2 gap-6 w-full max-w-md mx-auto relative">
                    <div className="bg-[#050505] border border-white/10 p-5 rounded-lg h-32 relative overflow-hidden flex flex-col justify-between">
                       <div className="text-[#888] text-xs uppercase tracking-widest">Total Requests</div>
                       <div className="text-3xl font-black text-white relative z-10">42,891</div>
                       <svg className="absolute bottom-0 left-0 w-full h-16" preserveAspectRatio="none" viewBox="0 0 100 100">
                         <path className="c4-line1" d="M0 100 L20 80 L40 90 L60 40 L80 60 L100 20" fill="none" stroke="#00f0ff" strokeWidth="4" />
                       </svg>
                    </div>
                    <div className="bg-[#050505] border border-white/10 p-5 rounded-lg h-32 relative overflow-hidden flex flex-col justify-between">
                       <div className="text-[#888] text-xs uppercase tracking-widest">Threats Blocked</div>
                       <div className="text-3xl font-black text-red-500 relative z-10">1,402</div>
                       <svg className="absolute bottom-0 left-0 w-full h-16" preserveAspectRatio="none" viewBox="0 0 100 100">
                         <path className="c4-line2" d="M0 100 L20 90 L40 70 L60 80 L80 30 L100 10" fill="none" stroke="#ef4444" strokeWidth="4" />
                       </svg>
                    </div>
                  </div>
                </div>
              )}

              {/* CHAPTER 5 CONTENT: Compliance */}
              {activeChapter === 4 && (
                <div className="w-full flex flex-col items-center justify-center font-mono relative z-10 h-full">
                  <div className="w-full max-w-md bg-[#050505] border border-white/20 p-4 rounded-lg overflow-hidden h-48 relative shadow-[0_0_30px_rgba(0,0,0,1)]">
                    <div className="text-[#555] text-[10px] mb-2 border-b border-white/5 pb-2">/var/log/agentwatch/audit.log</div>
                    <div className="c5-logs text-[#00f0ff] text-xs flex flex-col gap-2 relative top-0">
                      <div className="c5-log opacity-0">[10:04:21] WARN: Blocked unauthorized fs.readFile</div>
                      <div className="c5-log opacity-0">[10:04:22] INFO: Agent session #4992 initiated</div>
                      <div className="c5-log opacity-0">[10:04:23] SEC : Semantic risk score calculated (98)</div>
                      <div className="c5-log opacity-0">[10:04:23] AUDIT: Rollback to S2 executed</div>
                      <div className="c5-log opacity-0 mt-4 text-black font-bold bg-[#e8ff47] px-2 py-1 inline-block uppercase tracking-widest text-center">Generating SOC2 Compliance Report...</div>
                    </div>
                  </div>
                  <div className="c5-pdf opacity-0 scale-0 mt-8 bg-[#00f0ff]/10 border border-[#00f0ff] text-[#00f0ff] px-6 py-3 rounded-full font-bold shadow-[0_0_30px_rgba(0,240,255,0.3)] flex items-center gap-3">
                    <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
                    SOC2_Audit_Log_2026.pdf
                  </div>
                </div>
              )}

            </div>

            {/* Video Controls Overlay */}
            <div className="absolute inset-x-0 bottom-0 p-6 bg-gradient-to-t from-black via-black/80 to-transparent flex flex-col gap-4 translate-y-4 opacity-0 group-hover:translate-y-0 group-hover:opacity-100 transition-all duration-300 z-30">
              {/* Progress Bar */}
              <div className="h-1.5 w-full bg-white/20 rounded-full overflow-hidden cursor-pointer group/progress relative">
                <div className="absolute inset-y-0 left-0 bg-white/10 w-full opacity-0 group-hover/progress:opacity-100 transition-opacity" />
                <div className="video-progress h-full bg-[#e8ff47] w-0 relative">
                  <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full shadow-[0_0_10px_rgba(255,255,255,0.8)] opacity-0 group-hover/progress:opacity-100 translate-x-1/2 transition-opacity" />
                </div>
              </div>
              <div className="flex justify-between items-center text-[#a8a8a8] text-sm font-mono">
                <div className="flex items-center gap-4">
                  <svg className="w-6 h-6 text-white cursor-pointer hover:text-[#e8ff47] transition-colors hover:scale-110 transform" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                  <div className="flex items-center gap-1">
                    <span className="video-time text-white font-bold">0:00</span>
                    <span className="opacity-50">/ 0:{[0, 3].includes(activeChapter) ? "05" : activeChapter === 1 ? "06" : "07"}</span>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <svg className="w-5 h-5 hover:text-[#00f0ff] cursor-pointer transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
                  <svg className="w-5 h-5 hover:text-[#00f0ff] cursor-pointer transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" /></svg>
                </div>
              </div>
            </div>

            {/* Play Button Overlay (fades out when "playing") */}
            <div className="play-overlay absolute inset-0 flex items-center justify-center bg-black/60 backdrop-blur-md z-40 pointer-events-none">
              <div className="w-24 h-24 rounded-full bg-[#e8ff47] flex items-center justify-center shadow-[0_0_60px_rgba(232,255,71,0.6)] transform hover:scale-110 transition-transform">
                <svg className="w-12 h-12 text-black ml-1" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M8 5v14l11-7z" />
                </svg>
              </div>
            </div>
          </div>
        </div>

      </div>
    </section>
  );
}
