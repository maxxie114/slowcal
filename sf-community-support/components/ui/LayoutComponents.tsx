import { cn } from "@/lib/utils";
import { ButtonHTMLAttributes } from "react";

export function HandwrittenText({ children, className, as: Component = "span" }: { children: React.ReactNode, className?: string, as?: React.ElementType }) {
    return (
        <Component className={cn("font-script font-bold text-ink-dark", className)}>
            {children}
        </Component>
    );
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: "primary" | "secondary" | "outline";
}

export function Button({ children, className, variant = "primary", ...props }: ButtonProps) {
    const variants = {
        primary: "bg-accent-dark text-white border-accent-dark hover:bg-accent-dark-hover hover:border-accent-dark-hover shadow-md",
        secondary: "bg-[#EDE8DB] text-ink-dark border-[#D4C4A8] hover:bg-[#E5DFD0]",
        outline: "bg-transparent text-ink-dark border-ink-medium hover:bg-paper-grid",
    };

    return (
        <button
            className={cn(
                "px-6 py-2 rounded-lg border-2 font-medium transition-all transform active:scale-95",
                "font-sans tracking-wide",
                variants[variant],
                className
            )}
            {...props}
        >
            {children}
        </button>
    );
}
