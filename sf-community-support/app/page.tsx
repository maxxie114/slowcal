import { LandingHero } from "@/components/landing/LandingHero";
import { PathCard } from "@/components/landing/PathCard";
import { Store, Users, HeartHandshake } from "lucide-react";
import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen py-10 px-4 flex flex-col items-center bg-paper-cream">
      <LandingHero />

      <div className="w-full max-w-4xl mx-auto px-4 mb-12">
        <div className="relative rounded-xl overflow-hidden shadow-lg border-4 border-white/50">
          <video
            src="/Cinematic_Drone_Video_Generation.mp4"
            autoPlay
            loop
            muted={false}
            controls={false}
            playsInline
            className="w-full h-auto"
          />
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto px-4 w-full">
        <Link href="/business-portal/onboarding" className="block h-full">
          <PathCard
            title="I am a local business"
            description="Access survival tools, risk assessment, and connect with your community."
            icon={<Store className="w-12 h-12 text-ink-dark" />}
            ctaText="Get Support"
            href="/business-portal/onboarding"
            variant="business"
          />
        </Link>

        <Link href="/discover" className="block h-full">
          <PathCard
            title="I want to support local"
            description="Discover local gems, see who needs help, and keep SF authentic."
            icon={<HeartHandshake className="w-12 h-12 text-ink-dark" />}
            ctaText="Explore Directory"
            href="/discover"
            variant="supporter"
          />
        </Link>
      </div>

      <div className="mt-20 text-center">
        <p className="font-mono text-sm text-ink-light">
          <span className="inline-block w-2 h-2 rounded-full bg-risk-high animate-pulse mr-2" />
          47 businesses need your help today
        </p>
      </div>
    </main>
  );
}
