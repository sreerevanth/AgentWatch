"use client";

import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import ScrollTrigger from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

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
      gsap.from(".playlist-item", {
        x: -40,
        opacity: 0,
        duration: 0.8,
        stagger: 0.15,
        ease: "power3.out",
        scrollTrigger: {
          trigger: containerRef.current,
          start: "top 60%",
          once: true
        }
      });
      gsap.from(playerRef.current, {
        scale: 0.95,
        opacity: 0,
        duration: 1,
        ease: "power4.out",
        scrollTrigger: {
          trigger: containerRef.current,
          start: "top 60%",
          once: true
        }
      });
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
        tl.to(".c1-msg1", { opacity: 1, y: 0, duration: 0.4 })
          .to(".c1-msg2", { opacity: 1, y: 0, duration: 0.4 }, "+=0.8")
          .to(".c1-file", { opacity: 0, scale: 0.5, stagger: 0.1, duration: 0.2 }, "+=0.5")
          .to(".c1-alert", { opacity: 1, scale: 1, duration: 0.5, ease: "elastic.out(1, 0.3)" }, "+=0.2");
          
        tl.to(".video-progress", { width: "100%", duration: tl.duration(), ease: "none" }, 0);
        tl.to(".video-time", { innerHTML: "0:04", duration: tl.duration(), snap: { innerHTML: 1 }, ease: "none" }, 0);
        
        tl.to([".c1-msg1", ".c1-msg2", ".c1-alert"], { opacity: 0, duration: 0.5 }, "+=2");
        tl.to(".c1-file", { opacity: 1, scale: 1, duration: 0 }, "<");
      } 
      else if (activeChapter === 1) {
        // CHAPTER 2: The Interceptor
        tl.to(".seq-1", { opacity: 1, duration: 0.2 })
          .to(".seq-2", { opacity: 1, duration: 0.4 }, "+=0.6")
          .to(".seq-3", { opacity: 1, y: -5, duration: 0.3, ease: "back.out(1.5)" }, "+=0.5")
          .to(".seq-4", { opacity: 1, duration: 0.3 }, "+=0.8")
          .to(".seq-5", { opacity: 1, scale: 1.05, duration: 0.3, ease: "back.out(2)" }, "+=0.4")
          .to(".seq-5", { scale: 1, duration: 0.2 });

        tl.to(".video-progress", { width: "100%", duration: tl.duration(), ease: "none" }, 0);
        tl.to(".video-time", { innerHTML: "0:05", duration: tl.duration(), snap: { innerHTML: 1 }, ease: "none" }, 0);

        tl.to([".seq-1", ".seq-2", ".seq-3", ".seq-4", ".seq-5"], { opacity: 0, duration: 0.5 }, "+=2");
      }
      else if (activeChapter === 2) {
        // CHAPTER 3: DAG Tracing
        tl.to(".dag-n1", { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2)" })
          .to(".dag-l1", { width: "40px", duration: 0.3 })
          .to(".dag-n2", { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2)" })
          .to(".dag-l2", { width: "40px", duration: 0.3 })
          .to(".dag-n3", { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2)" })
          .to(".dag-n3", { backgroundColor: "rgba(239, 68, 68, 0.2)", borderColor: "rgba(239, 68, 68, 1)", duration: 0.2 }, "+=0.4")
          .to(".dag-error", { opacity: 1, duration: 0.3 }, "<")
          .to(".dag-n3", { opacity: 0.3, scale: 0.8, duration: 0.5 }, "+=0.8")
          .to(".dag-error", { opacity: 0, duration: 0.2 }, "<")
          .to(".dag-l2", { width: "0px", duration: 0.3 }, "<")
          .to(".dag-n2", { boxShadow: "0 0 20px rgba(0, 240, 255, 0.8)", duration: 0.3 })
          .to(".dag-revert", { opacity: 1, duration: 0.3 });

        tl.to(".video-progress", { width: "100%", duration: tl.duration(), ease: "none" }, 0);
        tl.to(".video-time", { innerHTML: "0:06", duration: tl.duration(), snap: { innerHTML: 1 }, ease: "none" }, 0);

        tl.to([".dag-n1", ".dag-n2", ".dag-n3", ".dag-revert"], { opacity: 0, scale: 0, duration: 0.5 }, "+=2");
        tl.to(".dag-l1", { width: "0px", duration: 0 }, "<");
        tl.to(".dag-n2", { boxShadow: "none", duration: 0 }, "<");
        tl.to(".dag-n3", { backgroundColor: "rgba(0, 240, 255, 0.1)", borderColor: "rgba(0, 240, 255, 0.3)", duration: 0 }, "<");
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
        <div className="lg:w-1/3 flex flex-col gap-4">
          {CHAPTERS.map((chap, idx) => {
            const isActive = activeChapter === idx;
            return (
              <button
                key={chap.id}
                onClick={() => setActiveChapter(idx)}
                className={`playlist-item text-left p-6 rounded-2xl border transition-all duration-300 relative overflow-hidden group ${
                  isActive 
                    ? "bg-[#0a0a0a] border-[#e8ff47] shadow-[0_0_20px_rgba(232,255,71,0.15)]" 
                    : "bg-[#050505] border-white/5 hover:border-white/20 hover:bg-[#0a0a0a]"
                }`}
              >
                {isActive && (
                  <div className="absolute inset-0 bg-gradient-to-r from-[#e8ff47]/10 to-transparent pointer-events-none" />
                )}
                <div className={`text-[10px] font-mono font-bold uppercase tracking-widest mb-2 transition-colors ${isActive ? "text-[#00f0ff]" : "text-[#555]"}`}>
                  {chap.subtitle}
                </div>
                <h3 className={`text-xl font-bold mb-3 transition-colors ${isActive ? "text-white" : "text-[#888] group-hover:text-white"}`}>
                  {chap.title}
                </h3>
                <p className={`text-sm leading-relaxed transition-colors ${isActive ? "text-[#a8a8a8]" : "text-[#555]"}`}>
                  {chap.desc}
                </p>
              </button>
            );
          })}
        </div>

        {/* VIDEO PLAYER (Right Side) */}
        <div className="lg:w-2/3">
          <div 
            ref={playerRef} 
            className="relative w-full h-full min-h-[400px] md:min-h-[500px] rounded-3xl border border-white/10 bg-[#0a0a0a] overflow-hidden shadow-2xl group flex flex-col"
          >
            {/* Background Grid */}
            <div className="absolute inset-0 bg-[linear-gradient(rgba(232,255,71,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(232,255,71,0.02)_1px,transparent_1px)] bg-[size:32px_32px]" />
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,#0a0a0a_100%)]" />

            {/* Video Content Canvas */}
            <div className="absolute inset-0 p-8 flex items-center justify-center">
              
              {/* CHAPTER 1 CONTENT: Rogue AI */}
              {activeChapter === 0 && (
                <div className="w-full max-w-sm relative">
                  <div className="c1-msg1 opacity-0 translate-y-4 bg-white/10 text-white p-3 rounded-2xl rounded-tr-none self-end ml-auto mb-4 w-3/4 text-sm backdrop-blur">
                    Clean up my temp files.
                  </div>
                  <div className="c1-msg2 opacity-0 translate-y-4 bg-[#e8ff47]/20 text-[#e8ff47] border border-[#e8ff47]/30 p-3 rounded-2xl rounded-tl-none w-3/4 text-sm font-mono mb-6 backdrop-blur">
                    Sure! Executing: rm -rf /*
                  </div>
                  <div className="flex gap-4 justify-center">
                    {[1,2,3].map(i => (
                      <div key={i} className="c1-file w-12 h-16 bg-[#222] rounded flex items-center justify-center border border-white/10">
                        <div className="w-6 h-1 bg-[#444]" />
                      </div>
                    ))}
                  </div>
                  <div className="c1-alert opacity-0 absolute inset-0 flex items-center justify-center scale-50">
                    <div className="bg-red-500/20 backdrop-blur-md border-2 border-red-500 text-red-500 font-black text-4xl p-6 rounded-2xl uppercase tracking-widest shadow-[0_0_50px_rgba(239,68,68,0.5)] transform -rotate-12">
                      SYSTEM PURGED
                    </div>
                  </div>
                </div>
              )}

              {/* CHAPTER 2 CONTENT: The Interceptor */}
              {activeChapter === 1 && (
                <div className="w-full flex flex-col font-mono text-sm max-w-md mx-auto">
                  <div className="flex items-center gap-2 mb-6 border-b border-white/10 pb-4">
                    <div className="w-3 h-3 rounded-full bg-red-500/80" />
                    <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                    <div className="w-3 h-3 rounded-full bg-green-500/80" />
                    <span className="ml-2 text-[#555] text-xs font-semibold">agent-terminal</span>
                  </div>
                  <div className="space-y-4 text-left">
                    <div className="seq-1 opacity-0 text-[#a8a8a8]">
                      <span className="text-[#00f0ff]">$</span> agent run task --id 8492
                    </div>
                    <div className="seq-2 opacity-0 text-[#e5e2e1]">
                      [Agent] Planning steps...
                      <br/>
                      [Agent] Attempting to execute: <span className="text-red-400">rm -rf /var/www/*</span>
                    </div>
                    <div className="seq-3 opacity-0 mt-4 rounded border border-[#e8ff47]/50 bg-[#e8ff47]/10 p-4 text-[#e8ff47]">
                      ⚠️ AGENTWATCH INTERCEPT ⚠️
                      <br/>
                      <span className="text-[#a8a8a8]">Holding execution for reasoning audit...</span>
                    </div>
                    <div className="seq-4 opacity-0 text-[#00f0ff]">
                      [Auditor] Semantic Risk Score: 98/100
                      <br/>
                      [Auditor] Verdict: <span className="text-red-500 font-bold">DESTRUCTIVE_ACTION</span>
                    </div>
                    <div className="seq-5 opacity-0 p-3 bg-red-500/20 border border-red-500/50 text-red-500 font-bold text-center uppercase tracking-widest shadow-[0_0_20px_rgba(239,68,68,0.2)]">
                      Action Blocked Pre-Execution
                    </div>
                  </div>
                </div>
              )}

              {/* CHAPTER 3 CONTENT: DAG Tracing */}
              {activeChapter === 2 && (
                <div className="w-full flex flex-col items-center justify-center font-mono">
                  <div className="flex items-center">
                    <div className="dag-n1 opacity-0 scale-0 w-16 h-16 rounded-full border-2 border-[#00f0ff]/30 bg-[#00f0ff]/10 flex items-center justify-center text-[#00f0ff] font-bold shadow-[0_0_15px_rgba(0,240,255,0.2)]">
                      S1
                    </div>
                    <div className="dag-l1 w-0 h-1 bg-[#00f0ff]/50" />
                    <div className="dag-n2 opacity-0 scale-0 w-16 h-16 rounded-full border-2 border-[#00f0ff]/30 bg-[#00f0ff]/10 flex items-center justify-center text-[#00f0ff] font-bold shadow-[0_0_15px_rgba(0,240,255,0.2)] relative">
                      S2
                      <div className="dag-revert opacity-0 absolute -top-8 left-1/2 -translate-x-1/2 whitespace-nowrap text-[#e8ff47] text-xs font-bold bg-[#e8ff47]/20 px-2 py-1 rounded">
                        ROLLBACK TARGET
                      </div>
                    </div>
                    <div className="dag-l2 w-0 h-1 bg-[#00f0ff]/50" />
                    <div className="dag-n3 opacity-0 scale-0 w-16 h-16 rounded-full border-2 border-[#00f0ff]/30 bg-[#00f0ff]/10 flex items-center justify-center text-[#00f0ff] font-bold shadow-[0_0_15px_rgba(0,240,255,0.2)] relative">
                      S3
                      <div className="dag-error opacity-0 absolute -bottom-10 left-1/2 -translate-x-1/2 whitespace-nowrap text-red-500 text-xs font-bold bg-red-500/20 border border-red-500/50 px-2 py-1 rounded">
                        HALT_ERROR
                      </div>
                    </div>
                  </div>
                </div>
              )}

            </div>

            {/* Video Controls Overlay */}
            <div className="absolute inset-x-0 bottom-0 p-6 bg-gradient-to-t from-black via-black/80 to-transparent flex flex-col gap-4 translate-y-4 opacity-0 group-hover:translate-y-0 group-hover:opacity-100 transition-all duration-300">
              {/* Progress Bar */}
              <div className="h-1.5 w-full bg-white/20 rounded-full overflow-hidden cursor-pointer group/progress relative">
                <div className="absolute inset-y-0 left-0 bg-white/10 w-full opacity-0 group-hover/progress:opacity-100" />
                <div className="video-progress h-full bg-[#e8ff47] w-0 relative">
                  <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full shadow-lg opacity-0 group-hover/progress:opacity-100 translate-x-1/2" />
                </div>
              </div>
              <div className="flex justify-between items-center text-[#a8a8a8] text-sm font-mono">
                <div className="flex items-center gap-4">
                  <svg className="w-6 h-6 text-white cursor-pointer hover:text-[#e8ff47] transition-colors" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                  <div className="flex items-center gap-1">
                    <span className="video-time text-white">0:00</span>
                    <span className="opacity-50">/ 0:{activeChapter === 0 ? "04" : activeChapter === 1 ? "05" : "06"}</span>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <svg className="w-5 h-5 hover:text-white cursor-pointer transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
                  <svg className="w-5 h-5 hover:text-white cursor-pointer transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" /></svg>
                </div>
              </div>
            </div>

            {/* Play Button Overlay (fades out when "playing") */}
            <div className="play-overlay absolute inset-0 flex items-center justify-center bg-black/50 backdrop-blur-sm z-20 pointer-events-none">
              <div className="w-20 h-20 rounded-full bg-[#e8ff47] flex items-center justify-center shadow-[0_0_40px_rgba(232,255,71,0.5)] transform hover:scale-110 transition-transform">
                <svg className="w-10 h-10 text-black ml-1" viewBox="0 0 24 24" fill="currentColor">
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
