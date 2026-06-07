"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import ScrollTrigger from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

// — SVG icons (all use #e8ff47) —

function BrainIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <circle cx="8" cy="9" r="2" stroke="#e8ff47" strokeWidth="1.5" />
      <circle cx="20" cy="9" r="2" stroke="#e8ff47" strokeWidth="1.5" />
      <circle cx="14" cy="14" r="2" stroke="#e8ff47" strokeWidth="1.5" />
      <circle cx="8" cy="19" r="2" stroke="#e8ff47" strokeWidth="1.5" />
      <circle cx="20" cy="19" r="2" stroke="#e8ff47" strokeWidth="1.5" />
      <path
        d="M9.5 10.2L12.5 13M15.5 13L18.5 10.2M9.5 17.8L12.5 15M15.5 15L18.5 17.8"
        stroke="#e8ff47"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <path
        d="M14 3L4 7v6c0 6 4 10 10 11 6-1 10-5 10-11V7l-10-4z"
        stroke="#e8ff47"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M10 13.5l3 3 5-5.5"
        stroke="#e8ff47"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function RollbackIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <path
        d="M5 14a9 9 0 1 0 3.2-6.9"
        stroke="#e8ff47"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <path
        d="M4 4v5h5"
        stroke="#e8ff47"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function DAGIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <circle cx="6" cy="7" r="2.2" stroke="#e8ff47" strokeWidth="1.5" />
      <circle cx="22" cy="7" r="2.2" stroke="#e8ff47" strokeWidth="1.5" />
      <circle cx="14" cy="14" r="2.2" stroke="#e8ff47" strokeWidth="1.5" />
      <circle cx="6" cy="21" r="2.2" stroke="#e8ff47" strokeWidth="1.5" />
      <circle cx="22" cy="21" r="2.2" stroke="#e8ff47" strokeWidth="1.5" />
      <path
        d="M7.6 8.5L12.4 12.5M20.4 8.5L15.6 12.5M12.4 15.5L7.6 19.5M15.6 15.5L20.4 19.5"
        stroke="#e8ff47"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function DatabaseIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <ellipse cx="14" cy="6" rx="9" ry="3" stroke="#e8ff47" strokeWidth="1.5" />
      <path
        d="M5 6v8c0 1.66 4 3 9 3s9-1.34 9-3V6"
        stroke="#e8ff47"
        strokeWidth="1.5"
      />
      <path
        d="M5 14v8c0 1.66 4 3 9 3s9-1.34 9-3v-8"
        stroke="#e8ff47"
        strokeWidth="1.5"
      />
    </svg>
  );
}

function DocCheckIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <path
        d="M7 3h10l5 5v15a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"
        stroke="#e8ff47"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path d="M17 3v5h5" stroke="#e8ff47" strokeWidth="1.5" strokeLinejoin="round" />
      <path
        d="M9 16l3 3 6-6"
        stroke="#e8ff47"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

const features = [
  { Icon: BrainIcon,     title: "Reasoning Auditor", desc: "Independent model scores every step before it executes." },
  { Icon: ShieldIcon,    title: "Safety Engine",     desc: "Blocks 40+ dangerous patterns pre-execution, not post-hoc." },
  { Icon: RollbackIcon,  title: "One-Click Rollback",desc: "Git-backed checkpoints at every step. Irreversible becomes reversible." },
  { Icon: DAGIcon,       title: "Multi-Agent DAG",   desc: "Trace failures across agent boundaries. Find the root cause." },
  { Icon: DatabaseIcon,  title: "Causal Memory",     desc: "Cross-session reasoning trails. Why did we choose X last week?" },
  { Icon: DocCheckIcon,  title: "Compliance Ready",  desc: "GDPR, HIPAA, EU AI Act. One-click audit exports." },
];

export default function Features() {
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Cursor-following spotlight (cheap: pointermove listener per section, write CSS var)
    const onPointerMove = (e: PointerEvent) => {
      const cards = sectionRef.current?.querySelectorAll<HTMLElement>(".spotlight-card");
      cards?.forEach((card) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        // Only update if pointer is within or near the card to save work
        if (x > -200 && x < rect.width + 200 && y > -200 && y < rect.height + 200) {
          card.style.setProperty("--mx", `${x}px`);
          card.style.setProperty("--my", `${y}px`);
        }
      });
    };
    sectionRef.current?.addEventListener("pointermove", onPointerMove, { passive: true });

    if (prefersReduced) {
      return () => {
        sectionRef.current?.removeEventListener("pointermove", onPointerMove);
      };
    }

    const ctx = gsap.context(() => {
      gsap.from(".feat-title", {
        y: 30,
        opacity: 0,
        duration: 0.8,
        ease: "power3.out",
        scrollTrigger: { trigger: sectionRef.current, start: "top 80%", once: true },
      });

      // CRITICAL: animate ONLY the outer card. Use force3D + clearProps so hover
      // (which lives on .spotlight-card-inner) never collides with GSAP transforms.
      gsap.set(".feat-card-outer", { willChange: "transform, opacity" });
      gsap.from(".feat-card-outer", {
        y: 40,
        opacity: 0,
        duration: 0.7,
        stagger: 0.1,
        ease: "power3.out",
        force3D: true,
        scrollTrigger: { trigger: ".feat-grid", start: "top 85%", once: true },
        onComplete: () => {
          // Hand control back to CSS — eliminates the conflict that was causing flicker
          gsap.set(".feat-card-outer", { clearProps: "transform,opacity,willChange" });
        },
      });
    }, sectionRef);

    setTimeout(() => ScrollTrigger.refresh(), 100);
    return () => {
      sectionRef.current?.removeEventListener("pointermove", onPointerMove);
      ctx.revert();
    };
  }, []);

  return (
    <section
      id="features"
      ref={sectionRef}
      className="relative py-20 px-6"
      style={{
        background:
          "radial-gradient(ellipse 65% 70% at 50% 50%, rgba(10,10,10,0.82) 0%, rgba(10,10,10,0.4) 55%, transparent 92%), radial-gradient(ellipse 80% 60% at 30% 50%, rgba(188,210,14,0.03) 0%, transparent 70%)",
      }}
    >
      <div className="max-w-6xl mx-auto">
        <div className="flex items-end justify-between mb-12 gap-8 flex-wrap">
          <h2
            className="feat-title font-bold"
            style={{
              fontFamily: "var(--font-syne)",
              fontSize: "clamp(1.6rem, 3.5vw, 2.5rem)",
            }}
          >
            Everything you need.
          </h2>
          <span
            className="text-xs uppercase tracking-[0.2em] text-[#7a7a7a]"
            style={{ fontFamily: "var(--font-jetbrains)" }}
          >
            // 6 modules · production-grade
          </span>
        </div>

        <div className="feat-grid grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map(({ Icon, title, desc }, i) => (
            <div key={i} className="feat-card-outer">
              <div className="spotlight-card p-6 h-full">
                <div className="spotlight-card-inner h-full flex flex-col">
                  <div className="mb-4">
                    <Icon />
                  </div>
                  <h3
                    className="font-semibold text-[#e5e2e1] mb-2"
                    style={{ fontFamily: "var(--font-syne)" }}
                  >
                    {title}
                  </h3>
                  <p className="text-sm text-[#b8b8b8] leading-relaxed">{desc}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
