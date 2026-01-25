import { HandwrittenText } from "@/components/ui/LayoutComponents";
import { TapeStrip } from "@/components/ui/TapeStrip";
import Image from "next/image";

export function LandingHero() {
    return (
        <div className="relative w-full max-w-4xl mx-auto pt-20 pb-12 flex flex-col items-center text-center px-4">
            {/* Tape holding the header - Removed */}
            {/* <TapeStrip variant="horizontal" className="top-16 w-32 left-1/2 -translate-x-1/2 opacity-70 z-10" /> */}

            <div className="relative z-0 mb-8">
                <HandwrittenText as="h1" className="text-6xl md:text-8xl text-ink-dark mb-4 tracking-tight">
                    SlowCal
                </HandwrittenText>
                <p className="font-sans text-xl md:text-2xl text-ink-light tracking-wide font-light">
                    One mom & pop at a time.
                </p>
            </div>

            <div className="relative w-full h-48 md:h-64 opacity-80 mb-8 select-none">
                <Image
                    src="/illustrations/sf-skyline.svg"
                    alt="SF Skyline Sketch"
                    fill
                    className="object-contain"
                    priority
                />
            </div>

            <div className="max-w-xl mx-auto bg-paper-white/60 backdrop-blur-sm p-6 rounded-xl border border-white/50 shadow-sm relative">
                {/* <TapeStrip variant="corner-tl" className="w-16" /> */}
                <p className="text-lg md:text-xl text-ink-medium leading-relaxed">
                    Connecting community with culture.
                </p>
            </div>
        </div>
    );
}
