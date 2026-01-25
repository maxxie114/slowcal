"use client";

import { useState, useEffect } from "react";
import { ChevronDown, ChevronUp, ShieldAlert, ArrowRight, AlertCircle, MapPin, Building2, Calendar, FileText, Phone, Shield } from "lucide-react";
import { cn } from "@/lib/utils";
import { BusinessCard } from "@/components/directory/BusinessCard";
import { TapeStrip } from "@/components/ui/TapeStrip";
import Link from "next/link";
import { HandwrittenText } from "@/components/ui/LayoutComponents";
import { AnalysisResult } from "@/lib/api";

// Fallback mock data for when no real analysis exists
const MOCK_BUSINESS_FULL = {
    id: "dashboard-demo",
    name: "The Daily Grind",
    category: "cafe" as const,
    neighborhood: "Hayes Valley",
    riskLevel: "high" as const,
    riskScore: 78,
    photoUrl: "https://images.unsplash.com/photo-1509042239860-f550ce710b93?auto=format&fit=crop&q=80&w=800",
    tagline: "Serving the community since 2015",
    address: "500 Hayes St, San Francisco, CA",
    lat: 37.7765,
    lng: -122.4243,
};

export default function BusinessDashboardPage() {
    const [showRiskDetails, setShowRiskDetails] = useState(false);
    const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);

    useEffect(() => {
        // Try to load analysis result from sessionStorage
        const stored = sessionStorage.getItem('analysisResult');
        if (stored) {
            try {
                setAnalysisResult(JSON.parse(stored));
            } catch (e) {
                console.error('Failed to parse stored analysis result:', e);
            }
        }
    }, []);

    // Use real data if available, otherwise fall back to mock
    const businessData = analysisResult ? {
        id: analysisResult.case_id || "analyzed-business",
        name: analysisResult.business_name,
        category: "other" as const,  // Default to 'other' which is a valid Category
        neighborhood: analysisResult.neighborhood || "San Francisco",
        riskLevel: analysisResult.risk_level?.toLowerCase() as "low" | "medium" | "high",
        riskScore: Math.round(analysisResult.risk_score * 100),
        photoUrl: "https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&q=80&w=800",
        tagline: `Business in ${analysisResult.neighborhood || "San Francisco"}`,
        address: analysisResult.address,
        lat: 37.7749,
        lng: -122.4194,
    } : MOCK_BUSINESS_FULL;

    const riskLevel = analysisResult?.risk_level?.toUpperCase() || "HIGH";
    const riskScore = analysisResult ? Math.round(analysisResult.risk_score * 100) : 78;
    
    const getRiskColor = (level: string) => {
        switch (level) {
            case 'HIGH': return 'text-red-500';
            case 'MEDIUM': return 'text-orange-500';
            case 'LOW': return 'text-green-500';
            default: return 'text-gray-500';
        }
    };

    const getRiskBgColor = (level: string) => {
        switch (level) {
            case 'HIGH': return 'bg-red-50 border-red-200';
            case 'MEDIUM': return 'bg-orange-50 border-orange-200';
            case 'LOW': return 'bg-green-50 border-green-200';
            default: return 'bg-gray-50 border-gray-200';
        }
    };

    return (
        <main className="min-h-screen bg-[#FAFAFA] p-6 md:p-12 font-sans text-gray-900">
            <div className="max-w-6xl mx-auto space-y-12">
                
                {/* Header */}
                <header className="flex justify-between items-end border-b border-gray-200 pb-6">
                    <div>
                        <HandwrittenText as="h1" className="text-4xl text-ink-dark mb-2">
                            Dashboard
                        </HandwrittenText>
                        <p className="text-gray-500 font-light">Overview for {businessData.name}</p>
                    </div>
                    <div className="text-right hidden md:block">
                        <p className="text-xs font-mono text-gray-400 uppercase tracking-widest">
                            Last updated: {analysisResult ? new Date(analysisResult.analyzed_at).toLocaleString() : 'Just now'}
                        </p>
                    </div>
                </header>

                {/* Data Source Stats - Only show if real data */}
                {analysisResult && (
                    <section className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <div className="bg-white rounded-lg border border-gray-100 shadow-sm p-4 text-center">
                            <FileText className="w-6 h-6 text-blue-500 mx-auto mb-2" />
                            <p className="text-2xl font-bold text-gray-900">{analysisResult.permit_count_6m}</p>
                            <p className="text-xs text-gray-500">Permits (6mo radius)</p>
                        </div>
                        <div className="bg-white rounded-lg border border-gray-100 shadow-sm p-4 text-center">
                            <Phone className="w-6 h-6 text-orange-500 mx-auto mb-2" />
                            <p className="text-2xl font-bold text-gray-900">{analysisResult.complaint_count_6m}</p>
                            <p className="text-xs text-gray-500">311 Complaints</p>
                        </div>
                        <div className="bg-white rounded-lg border border-gray-100 shadow-sm p-4 text-center">
                            <Shield className="w-6 h-6 text-purple-500 mx-auto mb-2" />
                            <p className="text-2xl font-bold text-gray-900">{analysisResult.incident_count_6m}</p>
                            <p className="text-xs text-gray-500">SFPD Incidents</p>
                        </div>
                        <div className="bg-white rounded-lg border border-gray-100 shadow-sm p-4 text-center">
                            <MapPin className="w-6 h-6 text-green-500 mx-auto mb-2" />
                            <p className="text-2xl font-bold text-gray-900">{Math.round(analysisResult.match_confidence * 100)}%</p>
                            <p className="text-xs text-gray-500">Match Confidence</p>
                        </div>
                    </section>
                )}

                {/* Risk Section - Clean & Lean */}
                <section className={cn("bg-white rounded-lg border shadow-sm p-6 md:p-8", getRiskBgColor(riskLevel))}>
                    <div className="flex flex-col md:flex-row gap-8 items-start mb-6">
                        <div className="flex-1">
                            <h2 className="text-xl font-semibold flex items-center gap-2 mb-3 text-gray-900">
                                <ShieldAlert className={cn("w-5 h-5", getRiskColor(riskLevel))} />
                                Risk Assessment
                            </h2>
                            <p className="text-gray-600 leading-relaxed max-w-2xl">
                                {analysisResult?.strategy_summary || 
                                 "Your business is currently facing significant headwinds. Immediate action on lease negotiation is recommended."}
                            </p>
                        </div>
                        
                        <div className="flex-shrink-0 w-full md:w-auto flex flex-col items-end gap-4">
                            <div className="text-right">
                                <span className={cn("block text-3xl font-bold", getRiskColor(riskLevel))}>{riskLevel} Risk</span>
                                <span className="text-sm text-gray-400">Score: {riskScore}/100</span>
                            </div>
                            
                            <button 
                                onClick={() => setShowRiskDetails(!showRiskDetails)}
                                className="text-sm font-medium text-gray-500 hover:text-black transition-colors flex items-center gap-1"
                            >
                                {showRiskDetails ? "Hide breakdown" : "View breakdown"}
                                {showRiskDetails ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                            </button>
                        </div>
                    </div>

                    {showRiskDetails && (
                        <div className="pt-6 border-t border-gray-100 animate-in fade-in slide-in-from-top-2">
                            {analysisResult?.risk_drivers && analysisResult.risk_drivers.length > 0 ? (
                                <div className="space-y-4">
                                    <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4">Risk Drivers</h3>
                                    {analysisResult.risk_drivers.map((driver) => (
                                        <div key={driver.name} className="flex items-center justify-between p-3 bg-white rounded-lg border border-gray-100">
                                            <div className="flex items-center gap-3">
                                                <span className={cn(
                                                    "text-lg",
                                                    driver.trend === 'up' ? "text-red-500" : 
                                                    driver.trend === 'down' ? "text-green-500" : "text-gray-400"
                                                )}>
                                                    {driver.trend === 'up' ? '↑' : driver.trend === 'down' ? '↓' : '→'}
                                                </span>
                                                <span className="font-medium text-gray-700">{driver.name}</span>
                                            </div>
                                            <span className="text-sm text-gray-500">{Math.round(driver.contribution * 100)}% contribution</span>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="flex flex-col md:flex-row gap-8 md:gap-16">
                                    {/* Default risk factors if none from API */}
                                    <div className="flex-1 space-y-4">
                                        <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4">External Factors</h3>
                                        {[
                                            { name: "Location Vacancy", value: 85, color: "bg-red-500", label: "Critical" },
                                            { name: "Competition Density", value: 70, color: "bg-orange-500", label: "High" },
                                            { name: "Market Trend", value: 60, color: "bg-yellow-500", label: "Moderate" },
                                            { name: "Area Foot Traffic", value: 90, color: "bg-red-500", label: "Critical" },
                                            { name: "Economic Shift", value: 45, color: "bg-green-500", label: "Low" }
                                        ].map((factor) => (
                                            <div key={factor.name} className="space-y-1">
                                                <div className="flex justify-between text-xs font-medium text-gray-600">
                                                    <span>{factor.name}</span>
                                                    <span className={cn(
                                                        "px-1.5 py-0.5 rounded text-[10px] uppercase font-bold text-white", 
                                                        factor.color
                                                    )}>{factor.label}</span>
                                                </div>
                                                <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden">
                                                    <div 
                                                        className={cn("h-full rounded-full transition-all duration-1000", factor.color)} 
                                                        style={{ width: `${factor.value}%` }} 
                                                    />
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </section>

                {/* Split Row: Profile & Plan */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 md:gap-12 items-start">
                    
                    {/* Left: Business Profile (Using BusinessCard) */}
                    <div className="space-y-4">
                         <h3 className="font-serif italic text-xl text-gray-400 ml-2">Your Profile</h3>
                         <div className="max-w-md mx-auto lg:mx-0 w-full transform transition-all hover:-rotate-1">
                            <BusinessCard business={businessData} />
                         </div>
                    </div>

                    {/* Right: Survival Plan (Authentic & Beautiful) */}
                    <div className="space-y-4 h-full flex flex-col">
                        <h3 className="font-serif italic text-xl text-gray-400 ml-2">Survival Plan</h3>
                        <Link href="/business-portal/plan" className="block group flex-1">
                            <div className="relative h-full min-h-[400px] bg-[#FDFDF9] p-8 md:p-10 rounded-sm shadow-md border border-[#EBE6D8] flex flex-col transition-transform group-hover:scale-[1.01] group-hover:shadow-lg">
                                {/* Paper Texture & Tape */}
                                <div className="absolute inset-0 bg-paper-pattern opacity-50 rounded-sm" />
                                <TapeStrip variant="horizontal" className="absolute -top-3 left-1/2 -translate-x-1/2 w-32 opacity-90" />
                                
                                <div className="relative z-10 flex flex-col h-full items-center text-center">
                                    <div className="mb-6 opacity-80">
                                        <div className="w-16 h-16 rounded-full border-2 border-dashed border-ink-light flex items-center justify-center mx-auto">
                                            <span className="font-mono text-xs text-ink-light">PLAN</span>
                                        </div>
                                    </div>

                                    <HandwrittenText className="text-4xl mb-4 text-ink-dark">
                                        Operation: Thriving
                                    </HandwrittenText>

                                    <p className="font-serif text-lg text-ink-medium italic mb-8 max-w-xs leading-relaxed">
                                        "A step-by-step guide to helping {businessData.name} thrive."
                                    </p>

                                    <div className="w-full h-px bg-gray-200 mb-8" />

                                    <div className="space-y-4 w-full max-w-xs text-left mx-auto flex-1">
                                        {analysisResult?.actions && analysisResult.actions.length > 0 ? (
                                            // Show real actions from API
                                            analysisResult.actions.slice(0, 3).map((action, idx) => (
                                                <div key={idx} className="flex items-center gap-3 text-ink-dark">
                                                    <div className={cn(
                                                        "w-4 h-4 rounded-full border flex items-center justify-center",
                                                        action.impact === 'HIGH' ? "border-risk-high" : 
                                                        action.impact === 'MEDIUM' ? "border-orange-400" : "border-green-500"
                                                    )}>
                                                        <div className={cn(
                                                            "w-2 h-2 rounded-full",
                                                            action.impact === 'HIGH' ? "bg-risk-high animate-pulse" : 
                                                            action.impact === 'MEDIUM' ? "bg-orange-400" : "bg-green-500"
                                                        )} />
                                                    </div>
                                                    <span className="font-sans text-sm truncate">{action.action}</span>
                                                </div>
                                            ))
                                        ) : (
                                            // Fallback static items
                                            <>
                                                <div className="flex items-center gap-3 text-ink-medium">
                                                    <div className="w-4 h-4 rounded-full border border-gray-300 flex items-center justify-center">
                                                        <div className="w-2 h-2 bg-transparent rounded-full" />
                                                    </div>
                                                    <span className="font-sans text-sm line-through text-gray-400">Initial Assessment</span>
                                                </div>
                                                <div className="flex items-center gap-3 text-ink-dark font-medium">
                                                    <div className="w-4 h-4 rounded-full border border-risk-high flex items-center justify-center">
                                                        <div className="w-2 h-2 bg-risk-high rounded-full animate-pulse" />
                                                    </div>
                                                    <span className="font-sans text-sm">Lease Negotiation</span>
                                                </div>
                                                <div className="flex items-center gap-3 text-ink-medium">
                                                    <div className="w-4 h-4 rounded-full border border-gray-300 flex items-center justify-center">
                                                        <div className="w-2 h-2 bg-transparent rounded-full" />
                                                    </div>
                                                    <span className="font-sans text-sm">Community Outreach</span>
                                                </div>
                                            </>
                                        )}
                                        {analysisResult?.actions && analysisResult.actions.length > 3 && (
                                            <p className="text-xs text-gray-400 italic mt-2">
                                                +{analysisResult.actions.length - 3} more actions...
                                            </p>
                                        )}
                                    </div>

                                    <div className="mt-8 flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-ink-dark group-hover:gap-4 transition-all">
                                        Open Plan <ArrowRight className="w-4 h-4" />
                                    </div>
                                </div>
                                
                                {/* Corner stamp */}
                                {/* <div className="absolute bottom-6 right-6 opacity-10 rotate-[-15deg] pointer-events-none">
                                    <div className="w-20 h-20 border-4 border-black rounded-full flex items-center justify-center">
                                        <span className="font-black text-[10px] uppercase">Action Required</span>
                                    </div>
                                </div> */}
                            </div>
                        </Link>
                    </div>

                </div>
            </div>
        </main>
    );
}
