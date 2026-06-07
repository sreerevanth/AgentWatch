import Hero from "./components/Hero";
import TrustMetrics from "./components/TrustMetrics";
import Stats from "./components/Stats";
import Marquee from "./components/Marquee";
import HowItWorks from "./components/HowItWorks";
import Features from "./components/Features";
import Comparison from "./components/Comparison";
import QuickStart from "./components/QuickStart";
import Contributors from "./components/Contributors";

export default function Home() {
  return (
    <main className="relative">
      <Hero />
      <TrustMetrics />
      <Stats />
      <Marquee />
      <HowItWorks />
      <Features />
      <Comparison />
      <QuickStart />
      <Contributors />
    </main>
  );
}
