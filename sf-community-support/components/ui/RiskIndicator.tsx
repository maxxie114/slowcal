import { cn } from "@/lib/utils";

interface RiskIndicatorProps {
    level: "low" | "moderate" | "high" | "critical";
    className?: string;
    showLabel?: boolean;
}

export function RiskIndicator({ level, className, showLabel = true }: RiskIndicatorProps) {
    const config = {
        low: { dots: 1, color: "bg-risk-low", text: "text-risk-low", label: "Moderate Risk" }, // Prompt said Low => Sage Green
        moderate: { dots: 2, color: "bg-risk-medium", text: "text-risk-medium", label: "Elevated Risk" },
        high: { dots: 3, color: "bg-risk-high", text: "text-risk-high", label: "High Risk" },
        critical: { dots: 4, color: "bg-risk-critical", text: "text-risk-critical", label: "Critical" },
    };

    // Mapping level to dots (out of 4 for simplicity, or 5)
    // Let's use 5 circle visualization where filled depends on risk
    const maxDots = 5;
    const filledDots =
        level === "low" ? 2 :
            level === "moderate" ? 3 :
                level === "high" ? 4 : 5;

    const colorClass = config[level].color;

    return (
        <div className={cn("flex items-center gap-2", className)}>
            <div className="flex gap-1" aria-label={`Risk level: ${level}`}>
                {[...Array(maxDots)].map((_, i) => (
                    <div
                        key={i}
                        className={cn(
                            "w-2.5 h-2.5 rounded-full border border-ink-light/30",
                            i < filledDots ? colorClass : "bg-transparent"
                        )}
                    />
                ))}
            </div>
            {showLabel && (
                <span className={cn("font-mono text-xs uppercase tracking-wider font-semibold", config[level].text)}>
                    {level} Risk
                </span>
            )}
        </div>
    );
}
