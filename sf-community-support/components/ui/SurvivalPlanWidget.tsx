
"use client";

import { cn } from "@/lib/utils";
import { CheckCircle2, Circle } from "lucide-react";

interface ActionStep {
    id: string;
    title: string;
    description: string;
    completed?: boolean;
}

interface SurvivalPlanWidgetProps {
    className?: string;
    steps: ActionStep[];
}

export function SurvivalPlanWidget({ className, steps }: SurvivalPlanWidgetProps) {
    return (
        <div className={cn("relative bg-[#FDFDF9] border border-[#E2E0D4] shadow-sm p-8", className)}>
            {/* Paper Texture Overlay */}
            <div className="absolute inset-0 bg-paper-pattern opacity-30 pointer-events-none mix-blend-multiply" />

            {/* Document Headers */}
            <div className="relative mb-6 border-b-2 border-ink-light/10 pb-4">
                <div className="flex justify-between items-start">
                    <div>
                        <h2 className="font-script text-3xl font-bold text-ink-dark -rotate-1 mb-1">
                            Your Survival Plan
                        </h2>
                        <p className="font-sans text-sm text-ink-light">
                            Generated on {new Date().toLocaleDateString()}
                        </p>
                    </div>
                    <div className="font-mono text-xs text-risk-high border border-risk-high px-2 py-1 uppercase tracking-widest rounded-sm rotate-2">
                        Action Required
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="relative space-y-6">
                {steps.map((step, index) => (
                    <div key={step.id} className="group flex gap-4 items-start">
                        <div className="mt-1 shrink-0 text-ink-light/40 group-hover:text-ink-medium transition-colors">
                            {step.completed ? (
                                <CheckCircle2 className="w-5 h-5 text-green-600" />
                            ) : (
                                <Circle className="w-5 h-5" />
                            )}
                        </div>
                        <div>
                            <h3 className={cn(
                                "font-serif font-bold text-lg text-ink-dark mb-1 group-hover:text-ink-dark transition-colors",
                                step.completed && "line-through text-ink-light"
                            )}>
                                {index + 1}. {step.title}
                            </h3>
                            <p className={cn(
                                "font-sans text-ink-medium leading-relaxed max-w-prose",
                                step.completed && "text-ink-light"
                            )}>
                                {step.description}
                            </p>
                        </div>
                    </div>
                ))}
            </div>

            {/* Footer Stamp */}
            <div className="absolute bottom-4 right-8 opacity-10 pointer-events-none rotate-[-12deg]">
                <div className="w-24 h-24 rounded-full border-4 border-ink-dark flex items-center justify-center">
                    <span className="font-black text-xs uppercase tracking-widest text-ink-dark">SlowCal Approved</span>
                </div>
            </div>
        </div>
    );
}
