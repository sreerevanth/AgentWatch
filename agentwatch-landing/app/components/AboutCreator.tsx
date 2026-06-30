"use client";

import Image from "next/image";
import { useEffect, useRef } from "react";
import gsap from "gsap";
import ScrollTrigger from "gsap/ScrollTrigger";

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

export default function AboutCreator() {
  const containerRef = useRef<HTMLElement>(null);
  
  useEffect(() => {
    const ctx = gsap.context(() => {
      // Avatar entrance animation
      gsap.fromTo(".creator-avatar",
        { scale: 0.5, opacity: 0, rotation: -45 },
        {
          scale: 1, opacity: 1, rotation: 0, duration: 1.2,
          ease: "elastic.out(1, 0.5)",
          scrollTrigger: {
            trigger: containerRef.current,
            start: "top 75%",
            once: true
          }
        }
      );
      
      // Floating animation for the avatar
      gsap.to(".creator-avatar", {
        y: -15,
        duration: 3,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut"
      });

      // Text stagger animation
      gsap.fromTo(".creator-text",
        { x: 30, opacity: 0 },
        {
          x: 0, opacity: 1, duration: 0.8, stagger: 0.15,
          ease: "power3.out",
          scrollTrigger: {
            trigger: containerRef.current,
            start: "top 75%",
            once: true
          }
        }
      );
    }, containerRef);
    
    return () => ctx.revert();
  }, []);

  return (
    <section ref={containerRef} className="relative z-10 py-32 px-6 max-w-7xl mx-auto border-t border-white/5 overflow-hidden">
      <div className="flex flex-col lg:flex-row gap-12 items-center">
        <div className="flex-1 w-full flex justify-center">
          <div className="creator-avatar w-64 h-64 rounded-full border-2 border-[#e8ff47] bg-[#0c0c0c] flex items-center justify-center overflow-hidden shadow-[0_0_40px_rgba(232,255,71,0.15)] relative">
            <div className="absolute inset-0 bg-gradient-to-tr from-[#00f0ff]/20 to-[#e8ff47]/20 z-0" />
            <Image
              src="https://github.com/sreerevanth.png"
              alt="sreerevanth"
              width={256}
              height={256}
              className="w-full h-full object-cover relative z-10"
              unoptimized
            />
          </div>
        </div>
        <div className="flex-1 w-full text-center lg:text-left">
          <h2 className="creator-text text-3xl md:text-4xl font-bold tracking-tight mb-4 text-white">
            Meet the Creator
          </h2>
          <div className="creator-text w-12 h-1 bg-gradient-to-r from-[#00f0ff] to-[#e8ff47] mx-auto lg:mx-0 mb-8 rounded-full" />
          <div className="text-[#888] leading-relaxed mb-6 space-y-4 text-sm">
            <p className="creator-text">
              I'm a developer focused on AI systems, developer tools, open-source software, and building technology that solves real-world problems.
            </p>
            <p className="creator-text">
              I'm the creator of AgentWatch and founder of VoidSwift, exploring challenges around AI reliability, transparency, and agentic systems. I strongly believe that the best way to grow as an engineer is to build in public and contribute to real projects.
            </p>
            <p className="creator-text font-mono text-xs uppercase tracking-widest text-white mt-8">
              Founder @VoidSwift • Creator of AgentWatch • Open Source Maintainer
              <br/><br/>
              <span className="text-[#e8ff47]">Ideas welcome. PRs preferred.</span>
            </p>
            <div className="creator-text pt-4">
              <a href="/about" className="inline-flex items-center gap-2 text-[#00f0ff] hover:text-white transition-colors font-mono text-sm uppercase tracking-widest">
                Read full bio →
              </a>
            </div>
          </div>
          <a href="#" className="creator-text inline-flex items-center gap-2 text-[#00f0ff] hover:text-white transition-colors font-mono text-sm uppercase tracking-widest">
            Follow on X
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 8l4 4m0 0l-4 4m4-4H3" />
            </svg>
          </a>
        </div>
      </div>
    </section>
  );
}
