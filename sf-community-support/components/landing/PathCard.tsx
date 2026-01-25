import { PaperCard } from "@/components/ui/PaperCard";
import { Button } from "@/components/ui/LayoutComponents";
import { HandwrittenText } from "@/components/ui/LayoutComponents";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

interface PathCardProps {
    title: string;
    description: string;
    icon: React.ReactNode;
    ctaText: string;
    href: string;
    variant: "supporter" | "business";
}

export function PathCard({ title, description, icon, ctaText, href, variant }: PathCardProps) {
    return (
        <PaperCard className="flex flex-col items-center text-center h-full group" tapeVariant="none">
            <div className="mb-6 p-4 bg-paper-cream rounded-full border-2 border-dashed border-ink-light/30 group-hover:scale-110 transition-transform duration-300">
                {icon}
            </div>

            <HandwrittenText as="h2" className="text-3xl mb-3">
                {title}
            </HandwrittenText>

            <p className="text-ink-medium mb-8 flex-grow leading-relaxed">
                {description}
            </p>

            <div className="w-full">
                <Button
                    variant={variant === "supporter" ? "primary" : "secondary"}
                    className="w-full flex items-center justify-center gap-2 group-hover:gap-3 transition-all"
                >
                    {ctaText}
                    <ArrowRight className="w-4 h-4" />
                </Button>
            </div>
        </PaperCard>
    );
}
