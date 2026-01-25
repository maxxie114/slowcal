import { cn } from "@/lib/utils";

interface TapeStripProps {
    className?: string; // For positioning
    variant?: "corner-tl" | "corner-tr" | "corner-bl" | "corner-br" | "horizontal" | "vertical";
    width?: string;
}

export function TapeStrip({ className, variant = "horizontal", width }: TapeStripProps) {
    // Base rotation mappings based on the prompt's suggestions
    // We encourage slight manual overrides via className for more randomness
    const variantStyles = {
        "corner-tl": "-rotate-[35deg] -left-3 -top-3",
        "corner-tr": "rotate-[35deg] -right-3 -top-3",
        "corner-bl": "rotate-[35deg] -left-3 -bottom-3",
        "corner-br": "-rotate-[35deg] -right-3 -bottom-3",
        "horizontal": "-rotate-2",
        "vertical": "rotate-[88deg]",
    };

    return (
        <div
            className={cn(
                "tape absolute h-8",
                variantStyles[variant],
                width ? width : "w-24", // Default width
                className
            )}
            aria-hidden="true"
        />
    );
}
