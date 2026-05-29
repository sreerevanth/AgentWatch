"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import ScrollTrigger from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

function CaptureIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="3" fill="#e8ff47" />
      <path
        d="M12 2v3M12 19v3M2 12h3M19 12h3"
        stroke="#e8ff47"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M4.93 4.93l2.12 2.12M16.95 16.95l2.12 2.12M4.93 19.07l2.12-2.12M16.95 7.05l2.12-2.12"
        stroke="#e8ff47"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function ScoreIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"
        stroke="#e8ff47"
        strokeWidth="2"
      />
      <path
        d="M9 12l2 2 4-4"
        stroke="#e8ff47"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function BlockIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 2L3 7v5c0 5.25 3.75 10.15 9 11.25C17.25 22.15 21 17.25 21 12V7L12 2z"
        stroke="#e8ff47"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <path
        d="M9 12h6M12 9v6"
        stroke="#e8ff47"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

const callouts = [
  {
    Icon: CaptureIcon,
    title: "Captures every reasoning step",
    desc: "Every thought, tool call, and decision is intercepted before execution.",
  },
  {
    Icon: ScoreIcon,
    title: "Independent model scores it",
    desc: "A second AI model evaluates the reasoning independently — no conflicts of interest.",
  },
  {
    Icon: BlockIcon,
    title: "Blocks dangerous actions before they run",
    desc: "Pre-execution veto power. Not alerts. Not logs. A hard stop.",
  },
];

export default function HowItWorks() {
  const sectionRef = useRef<HTMLElement>(null);
  const line1Ref = useRef<SVGPathElement>(null);
  const line2Ref = useRef<SVGPathElement>(null);
  const diagramRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) return;

    const ctx = gsap.context(() => {
      gsap.from(".hiw-title", {
        y: 40,
        opacity: 0,
        duration: 0.8,
        ease: "power3.out",
        scrollTrigger: {
          trigger: sectionRef.current,
          start: "top 80%",
          once: true,
        },
      });

      [line1Ref.current, line2Ref.current].forEach((line) => {
        if (!line) return;
        const length = line.getTotalLength?.() ?? 100;
        gsap.set(line, {
          strokeDasharray: length,
          strokeDashoffset: length,
        });
        gsap.to(line, {
          strokeDashoffset: 0,
          duration: 1.2,
          ease: "power2.inOut",
          scrollTrigger: {
            trigger: diagramRef.current,
            start: "top 80%",
            once: true,
          },
        });
      });

      gsap.from(".hiw-callout", {
        y: 40,
        opacity: 0,
        duration: 0.7,
        stagger: 0.15,
        ease: "power3.out",
        scrollTrigger: {
          trigger: ".hiw-callouts",
          start: "top 85%",
          once: true,
        },
      });
    }, sectionRef);

    setTimeout(() => ScrollTrigger.refresh(), 100);
    return () => ctx.revert();
  }, []);

  return (
    <section
      id="how-it-works"
      ref={sectionRef}
      className="py-16 px-6"
      style={{
        background:
          "radial-gradient(ellipse 65% 65% at 50% 50%, rgba(10,10,10,0.85) 0%, rgba(10,10,10,0.45) 55%, transparent 90%), linear-gradient(180deg, transparent 0%, rgba(232,255,71,0.02) 50%, transparent 100%)",
      }}
    >
      <div className="max-w-5xl mx-auto">
        <h2
          className="hiw-title text-center font-bold mb-12"
          style={{
            fontFamily: "var(--font-syne)",
            fontSize: "clamp(1.6rem, 3.5vw, 2.5rem)",
            textWrap: "balance",
          }}
        >
          Pre-execution blocking is{" "}
          <span className="gradient-text">the only way.</span>
        </h2>

        {/* Flow diagram */}
        <div ref={diagramRef} className="flex flex-col items-center mb-14">
          <div className="flex items-center gap-0 w-full max-w-2xl justify-center">
            <div className="flex-shrink-0">
              <div className="px-5 py-3 rounded-lg dark-glass text-sm text-[#a8a8a8]">
                Your Agent
              </div>
            </div>

            <div className="flex-1 flex items-center justify-center px-2 min-w-[40px]">
              <svg viewBox="0 0 60 20" className="w-full max-w-[80px] h-5">
                <path
                  ref={line1Ref}
                  d="M0 10 L50 10"
                  stroke="#e8ff47"
                  strokeWidth="1.5"
                  fill="none"
                  strokeLinecap="round"
                />
                <polygon points="46,6 54,10 46,14" fill="#e8ff47" />
              </svg>
            </div>

            <div className="flex-shrink-0">
              <div
                className="px-7 py-4 rounded-xl border-2 border-[#e8ff47] animate-pulse-glow relative"
                style={{
                  fontFamily: "var(--font-syne)",
                  background: "rgba(10,10,10,0.92)",
                  backdropFilter: "blur(14px)",
                  WebkitBackdropFilter: "blur(14px)",
                }}
              >
                <span className="text-base font-bold gradient-text">
                  AgentWatch
                </span>
                <div className="absolute inset-0 rounded-xl opacity-20 bg-[#e8ff47] blur-lg pointer-events-none" />
              </div>
            </div>

            <div className="flex-1 flex items-center justify-center px-2 min-w-[40px]">
              <svg viewBox="0 0 60 20" className="w-full max-w-[80px] h-5">
                <path
                  ref={line2Ref}
                  d="M0 10 L50 10"
                  stroke="#e8ff47"
                  strokeWidth="1.5"
                  fill="none"
                  strokeLinecap="round"
                />
                <polygon points="46,6 54,10 46,14" fill="#e8ff47" />
              </svg>
            </div>

            <div className="flex-shrink-0">
              <div className="px-5 py-3 rounded-lg dark-glass text-sm text-[#a8a8a8]">
                The World
              </div>
            </div>
          </div>
        </div>

        {/* Callouts */}
        <div className="hiw-callouts grid grid-cols-1 md:grid-cols-3 gap-6">
          {callouts.map(({ Icon, title, desc }, i) => (
            <div
              key={i}
              className="hiw-callout dark-glass flex flex-col gap-3 p-6 rounded-xl"
            >
              <Icon />
              <h3
                className="font-semibold text-[#e5e2e1]"
                style={{ fontFamily: "var(--font-syne)" }}
              >
                {title}
              </h3>
              <p className="text-sm text-[#b0b0b0] leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
