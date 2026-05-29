"use client";

import { usePathname } from "next/navigation";
import ThreeBackground from "./ThreeBackground";
import EdgeTraces from "./EdgeTraces";

/**
 * Conditional neural atmosphere.
 *
 * Renders the full Three.js neural canvas + corner edge traces on every
 * route EXCEPT /about. On the About page the background is intentionally
 * a clean black canvas — only the click ripple (mounted separately in
 * layout.tsx) remains as an interactive accent.
 */
export default function Atmosphere() {
  const pathname = usePathname();
  const hidden = pathname?.startsWith("/about");
  if (hidden) return null;
  return (
    <>
      <ThreeBackground />
      <EdgeTraces />
    </>
  );
}
