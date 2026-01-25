"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, MapPin, Building2, Store, Loader2, AlertCircle, CheckCircle } from "lucide-react";
import { analyzeBusinessRisk, AnalysisResult } from "@/lib/api";

const INDUSTRIES = [
    "Retail",
    "Food & Beverage",
    "Service",
    "Healthcare",
    "Technology",
    "Other"
];

type AnalysisState = 'idle' | 'analyzing' | 'success' | 'error';

export default function OnboardingPage() {
    const router = useRouter();
    const [formData, setFormData] = useState({
        name: "",
        address: "",
        industry: "",
        yearsInBusiness: ""
    });
    const [suggestions, setSuggestions] = useState<string[]>([]);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [analysisState, setAnalysisState] = useState<AnalysisState>('idle');
    const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

    const handleAddressChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value;
        setFormData({ ...formData, address: value });

        if (debounceTimer.current) {
            clearTimeout(debounceTimer.current);
        }

        if (value.length > 2) {
            setIsLoading(true);
            debounceTimer.current = setTimeout(async () => {
                try {
                    // Using Nominatim OpenStreetMap API (Free)
                    const response = await fetch(
                        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(value + ", San Francisco, CA")}&limit=5&countrycodes=us`,
                        {
                            headers: {
                                "User-Agent": "SlowCal-App"
                            }
                        }
                    );
                    const data = await response.json();
                    setSuggestions(data.map((item: any) => item.display_name));
                    setShowSuggestions(true);
                } catch (error) {
                    console.error("Error fetching addresses:", error);
                    setSuggestions([]);
                } finally {
                    setIsLoading(false);
                }
            }, 500);
        } else {
            setSuggestions([]);
            setShowSuggestions(false);
            setIsLoading(false);
        }
    };

    const selectAddress = (addr: string) => {
        setFormData({ ...formData, address: addr });
        setShowSuggestions(false);
    };

    const handleAnalyze = async () => {
        if (!formData.name || !formData.address) {
            setError("Please enter your business name and address");
            return;
        }

        setAnalysisState('analyzing');
        setError(null);

        try {
            const result = await analyzeBusinessRisk({
                business_name: formData.name,
                address: formData.address,
                industry: formData.industry || undefined,
                years_in_business: formData.yearsInBusiness ? parseInt(formData.yearsInBusiness) : undefined
            });

            setAnalysisResult(result);
            setAnalysisState('success');

            // Store result in sessionStorage for dashboard
            sessionStorage.setItem('analysisResult', JSON.stringify(result));

            // Navigate to dashboard after short delay
            setTimeout(() => {
                router.push("/business-portal/dashboard");
            }, 2500);

        } catch (err) {
            console.error("Analysis failed:", err);
            setError(err instanceof Error ? err.message : "Analysis failed. Please try again.");
            setAnalysisState('error');
        }
    };

    const getRiskColorClass = (level: string) => {
        switch (level?.toUpperCase()) {
            case 'HIGH': return 'text-red-500 bg-red-50';
            case 'MEDIUM': return 'text-orange-500 bg-orange-50';
            case 'LOW': return 'text-green-500 bg-green-50';
            default: return 'text-gray-500 bg-gray-50';
        }
    };

    return (
        <main className="min-h-screen bg-[#FAFAFA] flex flex-col items-center justify-center p-4">
            <div className="w-full max-w-xl bg-white rounded-xl shadow-sm border border-gray-100 p-8 md:p-12">
                
                {analysisState === 'analyzing' ? (
                    <div className="text-center py-12">
                        <Loader2 className="w-16 h-16 text-black animate-spin mx-auto mb-6" />
                        <h2 className="text-2xl font-bold text-gray-900 mb-3">Analyzing Your Business</h2>
                        <p className="text-gray-500 max-w-sm mx-auto">
                            We're pulling data from SF Open Data, running our risk model, and generating your personalized survival plan...
                        </p>
                        <div className="mt-8 space-y-3 text-sm text-gray-400">
                            <p className="animate-pulse">📊 Querying business registry...</p>
                            <p className="animate-pulse">🏗️ Checking permit activity...</p>
                            <p className="animate-pulse">📞 Analyzing 311 complaints...</p>
                            <p className="animate-pulse">🤖 Running AI risk model...</p>
                        </div>
                    </div>
                ) : analysisState === 'success' && analysisResult ? (
                    <div className="text-center py-8">
                        <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-6" />
                        <h2 className="text-2xl font-bold text-gray-900 mb-3">Analysis Complete!</h2>
                        
                        <div className={`inline-block px-6 py-3 rounded-full text-lg font-bold mb-6 ${getRiskColorClass(analysisResult.risk_level)}`}>
                            {analysisResult.risk_level} RISK ({Math.round(analysisResult.risk_score * 100)}%)
                        </div>

                        <div className="bg-gray-50 rounded-lg p-4 mb-6 text-left">
                            <h3 className="font-medium text-gray-900 mb-2">{analysisResult.business_name}</h3>
                            <p className="text-sm text-gray-600">{analysisResult.address}</p>
                            <p className="text-sm text-gray-400">{analysisResult.neighborhood}</p>
                        </div>

                        <div className="grid grid-cols-3 gap-4 mb-6 text-center">
                            <div className="bg-blue-50 rounded-lg p-3">
                                <p className="text-2xl font-bold text-blue-600">{analysisResult.permit_count_6m}</p>
                                <p className="text-xs text-gray-500">Permits (6mo)</p>
                            </div>
                            <div className="bg-orange-50 rounded-lg p-3">
                                <p className="text-2xl font-bold text-orange-600">{analysisResult.complaint_count_6m}</p>
                                <p className="text-xs text-gray-500">311 Calls</p>
                            </div>
                            <div className="bg-purple-50 rounded-lg p-3">
                                <p className="text-2xl font-bold text-purple-600">{analysisResult.incident_count_6m}</p>
                                <p className="text-xs text-gray-500">Incidents</p>
                            </div>
                        </div>

                        <p className="text-gray-500 text-sm">Redirecting to your dashboard...</p>
                    </div>
                ) : (
                    <>
                        <div className="mb-8">
                            <h1 className="text-3xl font-bold text-gray-900 mb-2">Welcome to SlowCal</h1>
                            <p className="text-gray-500">Let's analyze your business risk profile.</p>
                        </div>

                        {error && (
                            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
                                <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                                <p className="text-sm text-red-700">{error}</p>
                            </div>
                        )}

                        <div className="space-y-6">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Business Name</label>
                                <div className="relative">
                                    <Store className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                    <input
                                        type="text"
                                        className="w-full pl-10 pr-4 py-3 rounded-lg border border-gray-200 focus:border-black focus:ring-1 focus:ring-black outline-none transition-all"
                                        placeholder="e.g. The Daily Grind"
                                        value={formData.name}
                                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    />
                                </div>
                            </div>

                            <div className="relative">
                                <label className="block text-sm font-medium text-gray-700 mb-2">Business Address</label>
                                <div className="relative">
                                    <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                    <input
                                        type="text"
                                        className="w-full pl-10 pr-4 py-3 rounded-lg border border-gray-200 focus:border-black focus:ring-1 focus:ring-black outline-none transition-all"
                                        placeholder="Start typing your address..."
                                        value={formData.address}
                                        onChange={handleAddressChange}
                                    />
                                    {isLoading && (
                                        <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 animate-spin" />
                                    )}
                                </div>
                                {showSuggestions && suggestions.length > 0 && (
                                    <div className="absolute z-10 w-full mt-1 bg-white border border-gray-100 rounded-lg shadow-lg max-h-60 overflow-auto">
                                        {suggestions.map((addr) => (
                                            <button
                                                key={addr}
                                                className="w-full text-left px-4 py-3 hover:bg-gray-50 text-sm text-gray-700 transition-colors"
                                                onClick={() => selectAddress(addr)}
                                            >
                                                {addr}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">Industry</label>
                                    <div className="relative">
                                        <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                        <select 
                                            className="w-full pl-10 pr-4 py-3 rounded-lg border border-gray-200 focus:border-black focus:ring-1 focus:ring-black outline-none transition-all appearance-none bg-white"
                                            value={formData.industry}
                                            onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
                                        >
                                            <option value="">Select...</option>
                                            {INDUSTRIES.map(i => <option key={i} value={i}>{i}</option>)}
                                        </select>
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">Years in Business</label>
                                    <input
                                        type="number"
                                        className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:border-black focus:ring-1 focus:ring-black outline-none transition-all"
                                        placeholder="e.g. 5"
                                        value={formData.yearsInBusiness}
                                        onChange={(e) => setFormData({ ...formData, yearsInBusiness: e.target.value })}
                                    />
                                </div>
                            </div>

                            <button
                                onClick={handleAnalyze}
                                className="w-full mt-8 bg-black text-white py-4 rounded-lg font-medium hover:bg-gray-800 transition-colors flex items-center justify-center gap-2"
                            >
                                Analyze My Business
                                <ArrowRight className="w-4 h-4" />
                            </button>
                        </div>
                    </>
                )}
            </div>
        </main>
    );
}
