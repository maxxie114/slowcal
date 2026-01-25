"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, MapPin, Building2, Store, Loader2 } from "lucide-react";

const INDUSTRIES = [
    "Retail",
    "Food & Beverage",
    "Service",
    "Healthcare",
    "Technology",
    "Other"
];

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
                        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(value)}&limit=5&countrycodes=us`,
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
            }, 500); // 500ms debounce
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

    const handleNext = () => {
        router.push("/business-portal/dashboard");
    };

    return (
        <main className="min-h-screen bg-[#FAFAFA] flex flex-col items-center justify-center p-4">
            <div className="w-full max-w-xl bg-white rounded-xl shadow-sm border border-gray-100 p-8 md:p-12">
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">Welcome to SlowCal</h1>
                    <p className="text-gray-500">Let's get your business profile set up.</p>
                </div>

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
                        onClick={handleNext}
                        className="w-full mt-8 bg-black text-white py-4 rounded-lg font-medium hover:bg-gray-800 transition-colors flex items-center justify-center gap-2"
                    >
                        Continue to Dashboard
                        <ArrowRight className="w-4 h-4" />
                    </button>
                </div>
            </div>
        </main>
    );
}
