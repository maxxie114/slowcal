import { cn } from "@/lib/utils";
import { TapeStrip } from "./TapeStrip";

interface PaperCardProps extends React.HTMLAttributes<HTMLDivElement> {
    tape?: boolean; // Whether to include default tape strips
    tapeVariant?: "single-top" | "corners" | "none";
}

export function PaperCard({
    children,
    className,
    tape = true,
    tapeVariant = "single-top",
    ...props
}: PaperCardProps) {
    return (
        <div
            className={cn(
                "relative bg-paper-white rounded-2xl shadow-paper p-6 transition-all duration-300 hover:-translate-y-px hover:shadow-lg",
                className
            )}
            {...props}
        >
            {/* Decorative Tape */}
            {tape && tapeVariant === "single-top" && (
                <TapeStrip className="left-1/2 -translate-x-1/2 -top-4 w-32" variant="horizontal" />
            )}

            {tape && tapeVariant === "corners" && (
                <>
                    <TapeStrip variant="corner-tl" className="w-20" />
                    <TapeStrip variant="corner-br" className="w-20" />
                </>
            )}

            {children}
        </div>
    );
}
