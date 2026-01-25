
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { PaperCard } from "@/components/ui/PaperCard";
import { ArrowRight, MapPin, Search } from "lucide-react";
import { cn } from "@/lib/utils";

// Mock data for SF address autocomplete
const MOCK_ADDRESSES = [
    "2233 Market St, San Francisco, CA",
    "500 Hayes St, San Francisco, CA",
    "1 Ferry Building, San Francisco, CA",
    "3301 Lyon St, San Francisco, CA",
    "3600 16th St, San Francisco, CA",
    "1000 Van Ness Ave, San Francisco, CA",
];

export default function BusinessOnboardingPage() {
    const router = useRouter();
    const [step, setStep] = useState<1 | 2>(1);
    const [businessName, setBusinessName] = useState("");
    const [address, setAddress] = useState("");
    const [suggestions, setSuggestions] = useState<string[]>([]);
    const [showSuggestions, setShowSuggestions] = useState(false);

    const handleAddressChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value;
        setAddress(value);

        if (value.length > 2) {
            const filtered = MOCK_ADDRESSES.filter(addr =>
                addr.toLowerCase().includes(value.toLowerCase())
            );
            setSuggestions(filtered);
            setShowSuggestions(true);
        } else {
            setSuggestions([]);
            setShowSuggestions(false);
        }
    };

    const selectAddress = (addr: string) => {
        setAddress(addr);
        setShowSuggestions(false);
    };

    const handleNext = () => {
        if (step === 1 && businessName.trim()) {
            setStep(2);
        } else if (step === 2 && address.trim()) {
            router.push("/business-portal/dashboard");
        }
    };

    return (
        <main className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
            {/* Background Decor */}
            <div className="absolute inset-0 pointer-events-none opacity-50 bg-paper-pattern" />

            <div className="w-full max-w-lg relative z-10 perspective-1000">
                <PaperCard
                    tape={true}
                    tapeVariant="corners"
                    className="p-8 sm:p-12 min-h-[400px] flex flex-col items-center justify-center text-center transition-all duration-500"
                >
                    <div className="mb-8 space-y-2">
                        <h1 className="font-script text-5xl text-ink-dark -rotate-2">
                            Let's find your business
                        </h1>
                        <p className="font-sans text-ink-light text-lg">
                            We'll help you verify your details in a snap.
                        </p>
                    </div>

                    <div className="w-full max-w-sm space-y-6">
                        <div className={`transition-all duration-500 absolute w-full max-w-sm left-1/2 -translate-x-1/2 ${step === 1 ? 'opacity-100 translate-y-0 relative' : 'opacity-0 -translate-y-10 pointer-events-none absolute'}`}>
                            <label htmlFor="businessName" className="sr-only">Business Name</label>
                            <div className="relative group">
                                <input
                                    id="businessName"
                                    type="text"
                                    value={businessName}
                                    onChange={(e) => setBusinessName(e.target.value)}
                                    placeholder="What's your business name?"
                                    className="w-full bg-transparent border-b-2 border-ink-light/30 py-3 text-xl font-medium text-center focus:outline-none focus:border-ink-dark transition-colors placeholder:text-ink-light/50"
                                    autoFocus
                                    onKeyDown={(e) => e.key === 'Enter' && handleNext()}
                                />
                                <Search className="absolute right-0 top-1/2 -translate-y-1/2 text-ink-light/50 w-5 h-5 group-focus-within:text-ink-dark transition-colors" />
                            </div>
                        </div>

                        <div className={`transition-all duration-500 w-full max-w-sm left-1/2 -translate-x-1/2 ${step === 2 ? 'opacity-100 translate-y-0 relative' : 'opacity-0 translate-y-10 pointer-events-none absolute'}`}>
                            <label htmlFor="address" className="sr-only">Business Address</label>
                            <div className="relative group">
                                <input
                                    id="address"
                                    type="text"
                                    value={address}
                                    onChange={handleAddressChange}
                                    placeholder="Where are you located?"
                                    className="w-full bg-transparent border-b-2 border-ink-light/30 py-3 text-xl font-medium text-center focus:outline-none focus:border-ink-dark transition-colors placeholder:text-ink-light/50"
                                    autoFocus={step === 2}
                                    onKeyDown={(e) => e.key === 'Enter' && handleNext()}
                                />
                                <MapPin className="absolute right-0 top-1/2 -translate-y-1/2 text-ink-light/50 w-5 h-5 group-focus-within:text-ink-dark transition-colors" />

                                {/* Autocomplete Dropdown */}
                                {showSuggestions && suggestions.length > 0 && (
                                    <div className="absolute top-full left-0 w-full bg-white rounded-md shadow-lg mt-2 border border-ink-light/10 overflow-hidden z-50 text-left">
                                        {suggestions.map((s, i) => (
                                            <button
                                                key={i}
                                                onClick={() => selectAddress(s)}
                                                className="w-full px-4 py-3 hover:bg-gray-50 text-sm text-ink-medium transition-colors border-b border-gray-100 last:border-0 text-left"
                                            >
                                                {s}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>

                        <button
                            onClick={handleNext}
                            disabled={step === 1 ? !businessName : !address}
                            className={cn(
                                "mt-8 group relative inline-flex items-center justify-center gap-2 px-8 py-3 bg-ink-dark text-paper-white font-medium rounded-full overflow-hidden transition-all duration-300 hover:w-full hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed",
                                // step === 2 ? "w-full" : "w-auto"
                                "w-full" // Keep it consistent
                            )}
                        >
                            <span>{step === 1 ? "Next Step" : "Go to Dashboard"}</span>
                            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                        </button>

                        {step === 2 && (
                            <button onClick={() => setStep(1)} className="text-sm text-ink-light underline decoration-dotted hover:text-ink-dark transition-colors">
                                Back to name
                            </button>
                        )}
                    </div>
                </PaperCard>
            </div>
        </main>
    );
}
