"use client";

import { useState, useEffect } from "react";
import { ArrowLeft, CheckCircle, AlertTriangle, FileText, ChevronRight, Loader2 } from "lucide-react";
import Link from "next/link";
import { HandwrittenText } from "@/components/ui/LayoutComponents";
import { TapeStrip } from "@/components/ui/TapeStrip";
import { cn } from "@/lib/utils";
import { AnalysisResult, StrategicAction } from "@/lib/api";

interface PlanSection {
    id: string;
    title: string;
    status: 'critical' | 'moderate' | 'completed';
    icon: typeof AlertTriangle;
    onePager: {
        title: string;
        problem: string;
        context: string;
        actionPlan: { step: number; text: string }[];
        resources: string[];
    };
}

// Format horizon string nicely
function formatHorizon(horizon: string): string {
    if (!horizon) return "Action Item";
    // Replace underscores with spaces and capitalize first letter of each word
    return horizon
        .replace(/_/g, ' ')
        .replace(/\b\w/g, char => char.toUpperCase());
}

// Group actions by horizon and convert to plan sections
function convertActionsToSections(actions: StrategicAction[]): PlanSection[] {
    if (!actions || actions.length === 0) {
        return DEFAULT_SECTIONS;
    }

    // Group actions by horizon
    const groupedByHorizon = actions.reduce((acc, action) => {
        const horizon = action.horizon || 'Other';
        if (!acc[horizon]) {
            acc[horizon] = [];
        }
        acc[horizon].push(action);
        return acc;
    }, {} as Record<string, StrategicAction[]>);

    // Convert grouped actions to sections
    return Object.entries(groupedByHorizon).map(([horizon, horizonActions], idx) => {
        // Determine overall status based on highest impact in the group
        const hasHigh = horizonActions.some(a => a.impact === 'HIGH');
        const hasMedium = horizonActions.some(a => a.impact === 'MEDIUM');
        const status = hasHigh ? 'critical' as const : hasMedium ? 'moderate' as const : 'completed' as const;

        // Build action steps from all actions in this horizon
        const actionSteps = horizonActions.map((action, i) => ({
            step: i + 1,
            text: action.action
        }));

        // Build problem/context from all actions
        const problems = horizonActions
            .filter(a => a.why)
            .map(a => a.why)
            .join(' ');
        
        const outcomes = horizonActions
            .filter(a => a.expected_outcome)
            .map(a => `• ${a.expected_outcome}`)
            .join('\n');

        return {
            id: `horizon-${idx}`,
            title: formatHorizon(horizon),
            status,
            icon: hasHigh ? AlertTriangle : hasMedium ? FileText : CheckCircle,
            onePager: {
                title: `${formatHorizon(horizon)} Action Plan`,
                problem: problems || "These areas require attention based on our risk analysis.",
                context: `${horizonActions.length} action${horizonActions.length > 1 ? 's' : ''} identified for this timeframe.\n\nExpected Outcomes:\n${outcomes || 'Improved business resilience and reduced risk.'}`,
                actionPlan: actionSteps.slice(0, 8), // Max 8 steps
                resources: []
            }
        };
    });
}

const DEFAULT_SECTIONS: PlanSection[] = [
    {
        id: "lease",
        title: "Commercial Lease",
        status: "critical",
        icon: AlertTriangle,
        onePager: {
            title: "Lease Renegotiation Strategy",
            problem: "Rent to Income ratio has exceeded 25%, putting the business in the critical risk zone.",
            context: "Commercial rents in Hayes Valley have dropped by 12% on average for new leases, but your current agreement is locked at 2019 rates. This disparity is costing you approximately $4,500/month.",
            actionPlan: [
                { step: 1, text: "Request a rent relief or deferral meeting with your landlord." },
                { step: 2, text: "Present the 'Market Rate Comparison' report (attached below)." },
                { step: 3, text: "Propose a percentage-rent model for the next 12 months." },
            ],
            resources: ["Market Rate Report.pdf", "Rent Relief Letter Template.docx"]
        }
    },
    {
        id: "outreach",
        title: "Community Outreach",
        status: "moderate",
        icon: FileText,
        onePager: {
            title: "Community Re-Engagement",
            problem: "Foot traffic has decreased by 15% despite stable local population.",
            context: "Analysis shows a disconnect with newer residents in the area. Your 'regulars' base is aging, and new tech workers in the area aren't aware of your history.",
            actionPlan: [
                { step: 1, text: "Launch 'Meet the Owner' weekly events." },
                { step: 2, text: "Partner with 3 nearby tech offices for morning coffee runs." },
                { step: 3, text: "Update window signage to tell your 20-year story." },
            ],
            resources: ["Event Flyer Template.pdf", "Social Media Kit.zip"]
        }
    },
    {
        id: "digital",
        title: "Digital Presence",
        status: "completed",
        icon: CheckCircle,
        onePager: {
            title: "Digital Modernization",
            problem: "Online discoverability was low for 'coffee near me' searches.",
            context: "You have successfully claimed your Google Business Profile and updated your Yelp hours. Reviews have increased by 20% in the last month.",
            actionPlan: [
                { step: 1, text: "Continue responding to all reviews within 24 hours." },
                { step: 2, text: "Post weekly photos of specials." },
            ],
            resources: []
        }
    }
];

export default function SurvivalPlanPage() {
    const [sections, setSections] = useState<PlanSection[]>(DEFAULT_SECTIONS);
    const [activeSection, setActiveSection] = useState<PlanSection>(DEFAULT_SECTIONS[0]);
    const [businessName, setBusinessName] = useState<string>("Your Business");
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Load analysis result from sessionStorage
        const stored = sessionStorage.getItem('analysisResult');
        if (stored) {
            try {
                const result: AnalysisResult = JSON.parse(stored);
                setBusinessName(result.business_name);
                
                if (result.actions && result.actions.length > 0) {
                    const convertedSections = convertActionsToSections(result.actions);
                    setSections(convertedSections);
                    setActiveSection(convertedSections[0]);
                }
            } catch (e) {
                console.error('Failed to parse stored analysis result:', e);
            }
        }
        setLoading(false);
    }, []);

    return (
        <main className="min-h-screen bg-[#F0F0EB] flex">
            {/* Sidebar Navigation */}
            <aside className="w-80 bg-[#FAFAFA] border-r border-gray-200 flex flex-col h-screen sticky top-0">
                <div className="p-6 border-b border-gray-100">
                    <Link href="/business-portal/dashboard" className="text-gray-500 hover:text-black flex items-center gap-2 text-sm mb-6 transition-colors">
                        <ArrowLeft className="w-4 h-4" /> Back to Dashboard
                    </Link>
                    <HandwrittenText as="h1" className="text-3xl">
                        Survival Plan
                    </HandwrittenText>
                    <p className="text-sm text-gray-400 mt-2 font-mono">CASE FILE #2991</p>
                </div>

                <nav className="flex-1 overflow-y-auto p-4 space-y-2">
                    {sections.map((section) => (
                        <button
                            key={section.id}
                            onClick={() => setActiveSection(section)}
                            className={cn(
                                "w-full text-left p-4 rounded-lg flex items-start gap-3 transition-all border",
                                activeSection.id === section.id 
                                    ? "bg-white border-gray-200 shadow-sm ring-1 ring-black/5" 
                                    : "hover:bg-gray-100 border-transparent text-gray-600"
                            )}
                        >
                            <div className={cn(
                                "mt-0.5 w-2 h-2 rounded-full",
                                section.status === 'critical' ? "bg-red-500 animate-pulse" :
                                section.status === 'moderate' ? "bg-orange-400" :
                                "bg-green-500"
                            )} />
                            <div>
                                <span className={cn(
                                    "block font-medium",
                                    activeSection.id === section.id ? "text-black" : "text-gray-700"
                                )}>
                                    {section.title}
                                </span>
                                <span className="text-xs text-gray-400 uppercase tracking-wider">
                                    {section.status}
                                </span>
                            </div>
                            {activeSection.id === section.id && (
                                <ChevronRight className="w-4 h-4 ml-auto text-gray-400" />
                            )}
                        </button>
                    ))}
                </nav>

                <div className="p-6 border-t border-gray-200 bg-gray-50">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-black text-white flex items-center justify-center font-bold font-mono text-sm">
                            {sections.length}
                        </div>
                        <div className="text-xs text-gray-500">
                            <p className="font-semibold text-gray-900">{businessName}</p>
                            <p>{sections.length} action items</p>
                        </div>
                    </div>
                </div>
            </aside>

            {/* Main Content - The "One Pager" */}
            <div className="flex-1 p-8 md:p-12 overflow-y-auto bg-paper-pattern">
                {loading ? (
                    <div className="flex items-center justify-center h-full">
                        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                    </div>
                ) : (
                <div className="max-w-3xl mx-auto">
                    <div className="relative bg-[#FDFDF9] min-h-[800px] shadow-2xl p-12 md:p-16 rotate-[0.5deg]">
                        {/* Decorative elements */}
                        <TapeStrip variant="corner-tl" className="-left-4 -top-4 w-32 opacity-80" />
                        <TapeStrip variant="corner-br" className="-right-4 -bottom-4 w-32 opacity-80" />
                        
                        {/* Content */}
                        <div className="absolute top-12 right-12 opacity-20 pointer-events-none hidden">
                            <div className="w-32 h-32 border-4 border-red-800 rounded-full flex items-center justify-center rotate-[-20deg]">
                                <span className="font-black text-lg text-red-800 uppercase text-center leading-none">
                                    Confidential<br/>Report
                                </span>
                            </div>
                        </div>

                        <header className="mb-12 border-b-2 border-gray-100 pb-8">
                            <div className="flex items-center gap-2 mb-4">
                                <span className="px-3 py-1 bg-black text-white text-xs font-bold uppercase tracking-widest">
                                    Module: {activeSection.title}
                                </span>
                                {activeSection.status === 'critical' && (
                                    <span className="px-3 py-1 bg-red-100 text-red-700 text-xs font-bold uppercase tracking-widest">
                                        Priority: High
                                    </span>
                                )}
                            </div>
                            <HandwrittenText as="h2" className="text-5xl text-ink-dark mb-6">
                                {activeSection.onePager.title}
                            </HandwrittenText>
                        </header>

                        <div className="prose prose-lg prose-stone max-w-none font-serif leading-relaxed text-ink-medium">
                            <div className="mb-10">
                                <h3 className="font-sans text-sm font-bold uppercase tracking-widest text-gray-400 mb-3">The Problem</h3>
                                <p className="text-xl text-ink-dark italic border-l-4 border-risk-high pl-6 py-2 bg-red-50/50">
                                    "{activeSection.onePager.problem}"
                                </p>
                            </div>

                            <div className="mb-12">
                                <h3 className="font-sans text-sm font-bold uppercase tracking-widest text-gray-400 mb-3">Context & Analysis</h3>
                                <p>{activeSection.onePager.context}</p>
                            </div>

                            <div className="mb-12">
                                <h3 className="font-sans text-sm font-bold uppercase tracking-widest text-gray-400 mb-6">Recommended Action Plan</h3>
                                <ul className="space-y-6 list-none pl-0">
                                    {activeSection.onePager.actionPlan.map((step) => (
                                        <li key={step.step} className="flex gap-6 items-start group">
                                            <div className="w-8 h-8 rounded-full border-2 border-ink-dark flex-shrink-0 flex items-center justify-center font-bold font-mono group-hover:bg-ink-dark group-hover:text-white transition-colors">
                                                {step.step}
                                            </div>
                                            <p className="mt-1">{step.text}</p>
                                        </li>
                                    ))}
                                </ul>
                            </div>

                            {activeSection.onePager.resources.length > 0 && (
                                <div className="mt-16 pt-8 border-t border-gray-200">
                                    <h3 className="font-sans text-sm font-bold uppercase tracking-widest text-gray-400 mb-4">Attached Resources</h3>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        {activeSection.onePager.resources.map((resource) => (
                                            <div key={resource} className="flex items-center gap-3 p-4 bg-gray-50 border border-gray-200 rounded hover:bg-white hover:shadow-sm transition-all cursor-pointer">
                                                <FileText className="w-5 h-5 text-gray-400" />
                                                <span className="text-sm font-medium underline decoration-gray-300 underline-offset-4">{resource}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
                )}
            </div>
        </main>
    );
}