"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import gsap from "gsap";
import ScrollTrigger from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

interface Contributor {
  login: string;
  avatar_url: string;
  html_url: string;
  contributions: number;
  tag: string;
}

const TAGS = [
  "Core Systems",
  "Infrastructure",
  "Security",
  "Observability",
  "Adapters",
  "Replay Studio",
  "Frontend",
];

// Stable tag assignment from username (hash → tag)
function tagFor(login: string): string {
  let h = 0;
  for (let i = 0; i < login.length; i++) h = (h * 31 + login.charCodeAt(i)) >>> 0;
  return TAGS[h % TAGS.length];
}

// Hardcoded mappings for known maintainers (overrides hash)
const KNOWN_TAGS: Record<string, string> = {
  sreerevanth: "Core Systems",
  anshul23102: "Adapters",
  Divyanshu3994: "Observability",
};

// Raw contributor shape from /contributors.json or the GitHub API (no tag yet).
type RawContributor = {
  login: string;
  avatar_url: string;
  html_url: string;
  contributions: number;
};

// Shape of the pre-generated public/contributors.json file.
interface ContributorsFile {
  contributors: RawContributor[];
  updated_at?: string;
  total?: number;
}

// Drop bots, attach a tag, and sort by contributions descending.
function normalize(list: RawContributor[]): Contributor[] {
  return list
    .filter((c) => c.login && !c.login.includes("[bot]"))
    .map((c) => ({
      login: c.login,
      avatar_url: c.avatar_url,
      html_url: c.html_url,
      contributions: c.contributions,
      tag: KNOWN_TAGS[c.login] ?? tagFor(c.login),
    }))
    .sort((a, b) => b.contributions - a.contributions);
}

// Fallback used if both the local file and the GitHub API are unavailable
const FALLBACK: Contributor[] = [
  { login: "sreerevanth",  avatar_url: "https://github.com/sreerevanth.png",  html_url: "https://github.com/sreerevanth",  contributions: 312, tag: "Core Systems" },
  { login: "anshul23102",  avatar_url: "https://github.com/anshul23102.png",  html_url: "https://github.com/anshul23102",  contributions: 47,  tag: "Adapters" },
  { login: "Divyanshu3994",avatar_url: "https://github.com/Divyanshu3994.png",html_url: "https://github.com/Divyanshu3994",contributions: 23,  tag: "Observability" },
];

const REPO = "sreerevanth/agentwatch";

export default function Contributors() {
  const sectionRef = useRef<HTMLElement>(null);
  const [contributors, setContributors] = useState<Contributor[]>(FALLBACK);
  const [total, setTotal] = useState<number>(FALLBACK.length);
  const [loading, setLoading] = useState(true);

  // Load contributors. Prefer the pre-generated /contributors.json (refreshed
  // by the update-contributors workflow — no GitHub rate limits). If that file
  // is missing or unreadable, fall back to hitting the GitHub API directly.
  useEffect(() => {
    let cancelled = false;

    async function loadFromGitHub(): Promise<Contributor[]> {
      const r = await fetch(`https://api.github.com/repos/${REPO}/contributors?per_page=100`);
      if (!r.ok) throw new Error(`GitHub API ${r.status}`);
      const data: RawContributor[] = await r.json();
      if (!Array.isArray(data) || data.length === 0) throw new Error("empty contributor list");
      return normalize(data);
    }

    async function load() {
      try {
        const r = await fetch("/contributors.json", { cache: "no-store" });
        if (!r.ok) throw new Error(`contributors.json ${r.status}`);
        const file: ContributorsFile = await r.json();
        if (!Array.isArray(file.contributors) || file.contributors.length === 0) {
          throw new Error("contributors.json empty");
        }
        const list = normalize(file.contributors);
        if (!cancelled) {
          setContributors(list);
          setTotal(file.total ?? list.length);
        }
      } catch {
        // File missing/unreadable — fall back to the GitHub API.
        try {
          const list = await loadFromGitHub();
          if (!cancelled) {
            setContributors(list);
            setTotal(list.length);
          }
        } catch {
          // Both sources failed — keep the hardcoded FALLBACK list.
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  // Total contributions across every contributor (not just the 9 shown).
  const totalContributions = contributors.reduce((sum, c) => sum + c.contributions, 0);

  // Animations
  useEffect(() => {
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) return;

    const ctx = gsap.context(() => {
      gsap.from(".contrib-title, .contrib-sub, .contrib-meta", {
        y: 30,
        opacity: 0,
        duration: 0.8,
        stagger: 0.12,
        ease: "power3.out",
        scrollTrigger: { trigger: sectionRef.current, start: "top 80%", once: true },
      });

      gsap.set(".contrib-card", { willChange: "transform, opacity" });
      gsap.from(".contrib-card", {
        y: 30,
        opacity: 0,
        duration: 0.6,
        stagger: 0.06,
        ease: "power3.out",
        scrollTrigger: { trigger: ".contrib-grid", start: "top 85%", once: true },
        onComplete: () => gsap.set(".contrib-card", { clearProps: "transform,opacity,willChange" }),
      });

      gsap.from(".contrib-cta", {
        y: 30,
        opacity: 0,
        duration: 0.8,
        ease: "power3.out",
        scrollTrigger: { trigger: ".contrib-cta", start: "top 90%", once: true },
      });
    }, sectionRef);

    setTimeout(() => ScrollTrigger.refresh(), 100);
    return () => ctx.revert();
  }, [contributors]);

  // Cursor spotlight on cards + cta
  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      sectionRef.current
        ?.querySelectorAll<HTMLElement>(".spotlight-card")
        .forEach((card) => {
          const r = card.getBoundingClientRect();
          const x = e.clientX - r.left;
          const y = e.clientY - r.top;
          if (x > -200 && x < r.width + 200 && y > -200 && y < r.height + 200) {
            card.style.setProperty("--mx", `${x}px`);
            card.style.setProperty("--my", `${y}px`);
          }
        });
    };
    sectionRef.current?.addEventListener("pointermove", onMove, { passive: true });
    return () => sectionRef.current?.removeEventListener("pointermove", onMove);
  }, [contributors]);

  return (
    <section
      id="contributors"
      ref={sectionRef}
      className="relative py-20 px-6"
      style={{
        background:
          "radial-gradient(ellipse 70% 75% at 50% 50%, rgba(10,10,10,0.85) 0%, rgba(10,10,10,0.42) 55%, transparent 92%), radial-gradient(ellipse 60% 50% at 50% 0%, rgba(232,255,71,0.04) 0%, transparent 60%)",
      }}
    >
      <div className="max-w-6xl mx-auto flex flex-col">
        <div className="text-center mb-12 max-w-3xl mx-auto">
          <div className="contrib-meta inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[#e8ff47]/20 bg-[#e8ff47]/5 mb-5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#e8ff47] live-dot" />
            <span
              className="text-[10px] uppercase tracking-[0.2em] text-[#e8ff47]"
              style={{ fontFamily: "var(--font-jetbrains)" }}
            >
              Built in public · growing in real time
            </span>
          </div>
          <h2
            className="contrib-title font-bold mb-4"
            style={{
              fontFamily: "var(--font-syne)",
              fontSize: "clamp(1.8rem, 4vw, 2.8rem)",
              textWrap: "balance",
              lineHeight: 1.15,
            }}
          >
            People Building The Future
            <br />
            <span className="gradient-text">Of Agent Safety</span>
          </h2>
          <p
            className="contrib-sub text-[#b8b8b8] text-base max-w-xl mx-auto"
            style={{ textWrap: "balance" }}
          >
            Early contributors helping shape AgentWatch. Built in public with
            open-source contributors. More joining every week.
          </p>

          {/* Live counts — contributors + total contributions */}
          <div className="contrib-meta mt-6 flex flex-wrap items-center justify-center gap-3">
            <span
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-[#e8ff47]/25 bg-[#e8ff47]/5 text-sm text-[#e8ff47]"
              style={{ fontFamily: "var(--font-jetbrains)" }}
            >
              <span className="font-semibold">{total}</span> contributors and growing
            </span>
            <span
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/10 bg-white/[0.02] text-sm text-[#b8b8b8]"
              style={{ fontFamily: "var(--font-jetbrains)" }}
            >
              <span className="font-semibold text-[#e5e2e1]">
                {totalContributions.toLocaleString()}
              </span>{" "}
              total contributions
            </span>
          </div>
        </div>

        {/* Grid */}
        <div className="contrib-grid grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-12">
          {contributors.slice(0, 9).map((c) => (
            <a
              key={c.login}
              href={c.html_url}
              target="_blank"
              rel="noreferrer"
              className="contrib-card"
            >
              <div className="spotlight-card p-5 h-full">
                <div className="spotlight-card-inner h-full flex items-center gap-4">
                  <div className="relative">
                    <Image
                      src={c.avatar_url}
                      alt={`@${c.login}`}
                      width={48}
                      height={48}
                      className="rounded-full border border-white/10"
                      unoptimized
                    />
                    <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-[#e8ff47] border-2 border-[#0d0d0d]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span
                        className="text-sm text-[#e5e2e1] font-semibold truncate"
                        style={{ fontFamily: "var(--font-syne)" }}
                      >
                        {c.login}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <span
                        className="text-[10px] uppercase tracking-[0.15em] px-2 py-0.5 rounded border border-[#e8ff47]/25 text-[#e8ff47] bg-[#e8ff47]/5"
                        style={{ fontFamily: "var(--font-jetbrains)" }}
                      >
                        {c.tag}
                      </span>
                      <span
                        className="text-xs text-[#8a8a8a]"
                        style={{ fontFamily: "var(--font-jetbrains)" }}
                      >
                        {c.contributions} commits
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </a>
          ))}

          {/* "Growing" placeholder card — only one, subtle */}
          {!loading && contributors.length < 9 && (
            <div className="contrib-card">
              <div
                className="rounded-2xl p-5 h-full border border-dashed border-white/8 flex items-center gap-4"
                style={{ background: "rgba(255,255,255,0.015)" }}
              >
                <div className="w-12 h-12 rounded-full border border-dashed border-white/15 flex items-center justify-center text-[#555] text-lg">
                  +
                </div>
                <div className="flex-1">
                  <div
                    className="text-sm text-[#666]"
                    style={{ fontFamily: "var(--font-syne)" }}
                  >
                    you?
                  </div>
                  <div
                    className="text-[10px] uppercase tracking-[0.15em] text-[#444] mt-1"
                    style={{ fontFamily: "var(--font-jetbrains)" }}
                  >
                    open issues available
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Community CTA */}
        <div className="contrib-cta">
          <div className="spotlight-card p-8 md:p-10">
            <div className="spotlight-card-inner flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="text-center md:text-left">
                <h3
                  className="font-bold mb-2"
                  style={{
                    fontFamily: "var(--font-syne)",
                    fontSize: "clamp(1.4rem, 2.5vw, 1.8rem)",
                  }}
                >
                  Want your name <span className="gradient-text">here?</span>
                </h3>
                <p className="text-sm text-[#b8b8b8]">
                  Open source. Apache 2.0. We review every PR.
                </p>
              </div>
              <div className="flex flex-wrap items-center justify-center gap-3">
                <a
                  href="https://discord.gg/ZbQ9m9HtnE"
                  target="_blank"
                  rel="noreferrer"
                  className="btn-magnetic btn-discord-pulse px-5 py-2.5 rounded-lg bg-[#5865F2] hover:bg-[#4752c4] text-white text-sm font-medium"
                >
                  Join Discord
                </a>
                <a
                  href={`https://github.com/${REPO}/issues`}
                  target="_blank"
                  rel="noreferrer"
                  className="btn-magnetic px-5 py-2.5 rounded-lg border border-white/15 text-[#e5e2e1] hover:border-[#e8ff47]/50 hover:text-[#e8ff47] text-sm font-medium transition-colors"
                >
                  View Open Issues
                </a>
                <a
                  href={`https://github.com/${REPO}/blob/main/CONTRIBUTING.md`}
                  target="_blank"
                  rel="noreferrer"
                  className="btn-magnetic px-5 py-2.5 rounded-lg bg-[#e8ff47] text-[#0a0a0a] hover:bg-[#bcd20e] text-sm font-semibold"
                  style={{ boxShadow: "0 0 14px rgba(232,255,71,0.18)" }}
                >
                  Start Contributing →
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
