"use client";

import { useEffect, useRef } from "react";
import Image from "next/image";
import gsap from "gsap";
import ScrollTrigger from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

// Mocked data for contributors based on user request.
const CONTRIBUTORS = [
  {
    username: "SHAURYASANYAL3",
    avatarUrl: "https://avatars.githubusercontent.com/u/128920982?v=4",
    role: "Creator & Maintainer",
    stats: {
      commits: 12,
      prs: 16,
      issues: 27
    },
    specialContribution: "Architected AgentWatch and built the core foundation.",
    highlights: [
      "PR #480: Feature/new landing UI",
      "PR #455: test(cli): Add tests and benchmarks",
      "PR #454: feat(cli): Add core CLI logic"
    ]
  },
  {
    username: "sreerevanth",
    avatarUrl: "https://avatars.githubusercontent.com/u/86904394?v=4",
    role: "Core Contributor",
    stats: {
      commits: 39,
      prs: 2,
      issues: 1
    },
    specialContribution: "Actively contributed to AgentWatch with 39 commits and 2 PRs.",
    highlights: [
      "PR #410: Create SECURITY.md",
      "PR #409: Create CODE_OF_CONDUCT.md"
    ]
  },
  {
    username: "Prateeks16",
    avatarUrl: "https://avatars.githubusercontent.com/u/153312544?v=4",
    role: "Contributor",
    stats: {
      commits: 11,
      prs: 11,
      issues: 0
    },
    specialContribution: "Actively contributed to AgentWatch with 11 commits and 11 PRs.",
    highlights: [
      "PR #450: feat(governance): tamper-evident audit log for RBAC",
      "PR #449: fix(cli): route all session subcommands through one Typer group",
      "PR #445: fix: break governance↔tracing circular import"
    ]
  },
  {
    username: "pavsoss",
    avatarUrl: "https://avatars.githubusercontent.com/u/230380953?v=4",
    role: "Contributor",
    stats: {
      commits: 12,
      prs: 3,
      issues: 2
    },
    specialContribution: "Actively contributed to AgentWatch with 12 commits and 3 PRs.",
    highlights: [
      "PR #458: feat(telemetry): enterprise OTLP reasoning trace export",
      "PR #407: feat(mcp): expose AgentWatch observability tools through MCP",
      "PR #404: feat(loop-detector): make loop threshold configurable"
    ]
  },
  {
    username: "anshul23102",
    avatarUrl: "https://avatars.githubusercontent.com/u/167362756?v=4",
    role: "Contributor",
    stats: {
      commits: 17,
      prs: 0,
      issues: 0
    },
    specialContribution: "Actively contributed to AgentWatch with 17 commits and 0 PRs.",
    highlights: [
      "Consistently improved codebase quality and reliability."
    ]
  },
  {
    username: "DebasmitaBose0",
    avatarUrl: "https://avatars.githubusercontent.com/u/144198639?v=4",
    role: "Contributor",
    stats: {
      commits: 15,
      prs: 0,
      issues: 2
    },
    highlights: [
      "Issue #382: Implement Semantic Cache for Repeated LLM Subtasks",
      "Issue #381: Implement HIPAA Compliance Mode with PHI Auto-Redaction"
    ],
    specialContribution: "Actively contributed to AgentWatch with 15 commits and 2 issues."
  },
  {
    username: "SakethSumanBathini",
    avatarUrl: "https://avatars.githubusercontent.com/u/178634012?v=4",
    role: "Contributor",
    stats: {
      commits: 7,
      prs: 4,
      issues: 0
    },
    highlights: [
      "PR #387: feat(api): wire CMP-005 SAML/RBAC enforcement into the API layer",
      "PR #386: feat(memory): add MEM-008 natural language causal-graph traversal",
      "PR #384: fix(security): resolve all 13 bandit warnings"
    ],
    specialContribution: "Actively contributed to AgentWatch with 7 commits and 4 PRs."
  },
  {
    username: "arcgod-design",
    avatarUrl: "https://avatars.githubusercontent.com/u/225413120?v=4",
    role: "Contributor",
    stats: {
      commits: 1,
      prs: 6,
      issues: 0
    },
    highlights: [
      "PR #460: feat: multi-tenant cloud architecture for AgentWatch Cloud",
      "PR #439: feat: allow custom session metadata enrichment in watch() API",
      "PR #438: feat: support exporting compliance audit logs as CSV"
    ],
    specialContribution: "Actively contributed to AgentWatch with 1 commits and 6 PRs."
  },
  {
    username: "prachishelke1312",
    avatarUrl: "https://avatars.githubusercontent.com/u/228935308?v=4",
    role: "Contributor",
    stats: {
      commits: 5,
      prs: 2,
      issues: 0
    },
    highlights: [
      "PR #408: refactor: reduce verbose Claude Code debug logging",
      "PR #392: refactor: reduce verbose Claude Code debug logging"
    ],
    specialContribution: "Actively contributed to AgentWatch with 5 commits and 2 PRs."
  },
  {
    username: "SHUBHAM2775",
    avatarUrl: "https://avatars.githubusercontent.com/u/161486999?v=4",
    role: "Contributor",
    stats: {
      commits: 7,
      prs: 0,
      issues: 0
    },
    highlights: [
      "Consistently improved codebase quality and reliability."
    ],
    specialContribution: "Actively contributed to AgentWatch with 7 commits and 0 PRs."
  }
];

export default function ContributorsPage() {
  const pageRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) return;

    const ctx = gsap.context(() => {
      // Epic Hero Entrance
      gsap.fromTo(".hero-content > *", 
        { y: 60, opacity: 0, scale: 0.9, rotationX: -30 },
        { y: 0, opacity: 1, scale: 1, rotationX: 0, duration: 1.5, stagger: 0.2, ease: "expo.out", transformOrigin: "center bottom" }
      );

      // Background Aura Pulse
      gsap.to(".bg-aura", {
        scale: 1.2,
        opacity: 0.15,
        duration: 4,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut"
      });

      // Cards Entrance and continuous float
      const cards = gsap.utils.toArray(".contributor-card");
      cards.forEach((card: any, i) => {
        gsap.fromTo(card, 
          { y: 100, opacity: 0, scale: 0.8, rotationY: 15 },
          { 
            y: 0, opacity: 1, scale: 1, rotationY: 0, 
            duration: 1.2, delay: i * 0.15, ease: "power4.out",
            scrollTrigger: {
              trigger: card,
              start: "top 85%",
            }
          }
        );

        // Continuous floating
        gsap.to(card, {
          y: "-=10",
          duration: 2 + Math.random(),
          repeat: -1,
          yoyo: true,
          ease: "sine.inOut",
          delay: Math.random() * 2
        });
      });
    }, pageRef);

    // 3D Tilt and Spotlight Effect
    const onPointerMove = (e: PointerEvent) => {
      pageRef.current?.querySelectorAll<HTMLElement>(".contributor-card").forEach((card) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        // Spotlight
        card.style.setProperty("--mx", `${x}px`);
        card.style.setProperty("--my", `${y}px`);

        // 3D Tilt (only if hovering over this specific card)
        if (x > 0 && x < rect.width && y > 0 && y < rect.height) {
          const rotateX = ((y / rect.height) - 0.5) * -15;
          const rotateY = ((x / rect.width) - 0.5) * 15;
          gsap.to(card, { rotationX: rotateX, rotationY: rotateY, duration: 0.5, ease: "power2.out", transformPerspective: 1000 });
        } else {
          gsap.to(card, { rotationX: 0, rotationY: 0, duration: 0.5, ease: "power2.out" });
        }
      });
    };

    pageRef.current?.addEventListener("pointermove", onPointerMove, { passive: true });

    return () => {
      ctx.revert();
      pageRef.current?.removeEventListener("pointermove", onPointerMove);
    };
  }, []);

  return (
    <main ref={pageRef} className="relative min-h-screen pt-32 pb-24 px-6 overflow-hidden perspective-1000 bg-[#050505] text-[#ededed] selection:bg-[#00f0ff]/30 selection:text-[#00f0ff]">
      {/* Background Grid & Vignette */}
      <div className="absolute inset-0 z-0 pointer-events-none" style={{
        backgroundImage: "linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)",
        backgroundSize: "64px 64px",
        backgroundPosition: "center center",
        maskImage: "radial-gradient(circle at center, black 20%, transparent 80%)",
        WebkitMaskImage: "radial-gradient(circle at center, black 20%, transparent 80%)"
      }} />
      <div className="bg-aura absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-[#00f0ff] rounded-full blur-[150px] opacity-[0.07] pointer-events-none z-0" />
      <div className="absolute inset-0 bg-[url('/noise.png')] opacity-[0.03] pointer-events-none mix-blend-overlay z-0" />

      <div className="max-w-[1000px] mx-auto relative z-10">
        <section className="mb-20 text-center hero-content" style={{ perspective: 1000 }}>
          <h1
            className="font-bold leading-[1.08] mb-5"
            style={{
              fontFamily: "var(--font-syne)",
              fontSize: "clamp(2rem, 5.2vw, 4rem)",
              background: "linear-gradient(135deg, #ffffff 0%, #e8ff47 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
              textWrap: "balance",
              filter: "drop-shadow(0 0 30px rgba(232, 255, 71, 0.4))"
            }}
          >
            Hall of Fame
          </h1>
          <p
            className="text-[#b8b8b8] max-w-xl mx-auto font-light"
            style={{ fontSize: "clamp(1rem, 2vw, 1.125rem)" }}
          >
            AgentWatch is built by an incredible open-source community. Here are the people making it happen.
          </p>
        </section>

        <div className="contributors-grid grid grid-cols-1 md:grid-cols-2 gap-8" style={{ perspective: 1000 }}>
          {CONTRIBUTORS.map((c, i) => (
            <div
              key={c.username}
              className="contributor-card dark-glass rounded-2xl p-6 sm:p-8 flex flex-col h-full border border-white/5 relative group cursor-crosshair transform-style-3d"
              style={{
                background: "linear-gradient(145deg, rgba(10,10,10,0.9) 0%, rgba(5,5,5,0.95) 100%)",
                boxShadow: "0 0 0 1px rgba(255,255,255,0.05), 0 20px 40px rgba(0,0,0,0.5)"
              }}
            >
              {/* Animated Border Gradient on Hover */}
              <div className="absolute -inset-[2px] rounded-2xl bg-gradient-to-r from-[#00f0ff] via-[#e8ff47] to-[#00f0ff] opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-sm pointer-events-none" style={{ zIndex: -1, backgroundSize: "200% 200%", animation: "gradientMove 3s linear infinite" }} />
              
              {/* Spotlight Follower */}
              <div 
                className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none z-0" 
                style={{
                  background: `radial-gradient(600px circle at var(--mx) var(--my), rgba(232, 255, 71, 0.08), transparent 40%)`
                }}
              />

              <div className="flex items-center gap-4 mb-6 relative z-10 translate-z-10">
                <div className="relative w-16 h-16 rounded-full p-[2px] bg-gradient-to-br from-[#00f0ff] to-[#e8ff47] group-hover:shadow-[0_0_20px_#00f0ff] transition-shadow duration-500">
                  <img
                    src={c.avatarUrl}
                    alt={c.username}
                    className="w-full h-full rounded-full object-cover border-2 border-[#050505]"
                  />
                </div>
                <div>
                  <h3
                    className="font-bold text-xl text-white mb-1 group-hover:text-[#e8ff47] transition-colors"
                    style={{ fontFamily: "var(--font-syne)", textShadow: "0 2px 10px rgba(0,0,0,0.5)" }}
                  >
                    @{c.username}
                  </h3>
                  <div
                    className="text-xs uppercase tracking-widest text-[#00f0ff]"
                    style={{ fontFamily: "var(--font-jetbrains)" }}
                  >
                    {c.role}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3 mb-6 relative z-10 translate-z-10">
                <div className="bg-[#050505]/80 rounded-xl p-3 text-center border border-white/5 group-hover:border-[#e8ff47]/30 transition-colors">
                  <div className="text-2xl font-bold text-white mb-1">{c.stats.commits}</div>
                  <div className="text-[9px] uppercase text-[#888] tracking-widest">Commits</div>
                </div>
                <div className="bg-[#050505]/80 rounded-xl p-3 text-center border border-white/5 group-hover:border-[#00f0ff]/30 transition-colors">
                  <div className="text-2xl font-bold text-white mb-1">{c.stats.prs}</div>
                  <div className="text-[9px] uppercase text-[#888] tracking-widest">PRs</div>
                </div>
                <div className="bg-[#050505]/80 rounded-xl p-3 text-center border border-white/5 group-hover:border-white/20 transition-colors">
                  <div className="text-2xl font-bold text-white mb-1">{c.stats.issues}</div>
                  <div className="text-[9px] uppercase text-[#888] tracking-widest">Issues</div>
                </div>
              </div>

              <div className="flex-1 relative z-10 translate-z-10">
                <p className="text-sm text-[#e5e2e1] mb-5 leading-relaxed bg-black/20 p-4 rounded-lg border border-white/5 group-hover:bg-[#e8ff47]/5 transition-colors">
                  <span className="font-bold text-[#e8ff47] block mb-1">Impact //</span>
                  {c.specialContribution}
                </p>

                <div className="space-y-3 mt-4">
                  <p className="text-[10px] font-bold text-[#888] uppercase tracking-[0.2em] mb-3">Notable Merges</p>
                  {c.highlights.map((h, index) => (
                    <div key={index} className="flex items-start gap-3 text-sm text-[#a8a8a8] group-hover:text-[#c0c0c0] transition-colors">
                      <svg className="w-4 h-4 text-[#00f0ff] flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                      <span className="leading-snug">{h}</span>
                    </div>
                  ))}
                </div>
              </div>

              <a
                href={`https://github.com/${c.username}`}
                target="_blank"
                rel="noreferrer"
                className="mt-6 w-full text-center py-3 rounded-lg bg-[#050505] border border-white/10 hover:border-[#e8ff47] hover:bg-[#e8ff47]/10 hover:text-[#e8ff47] transition-all text-xs font-bold uppercase tracking-widest relative z-10 translate-z-10 shadow-lg"
                style={{ fontFamily: "var(--font-jetbrains)" }}
              >
                View Profile
              </a>
            </div>
          ))}
        </div>
      </div>
      <style dangerouslySetInnerHTML={{__html: `
        .transform-style-3d { transform-style: preserve-3d; }
        .translate-z-10 { transform: translateZ(20px); }
        @keyframes gradientMove {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
      `}} />
    </main>
  );
}
