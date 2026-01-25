"use client";

import { useMemo } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { DirectoryHeader } from "@/components/directory/DirectoryHeader";
import { FilterBar } from "@/components/directory/FilterBar";
import { BusinessCard } from "@/components/directory/BusinessCard";
import { mockBusinesses } from "@/lib/mockData";
import { motion, AnimatePresence } from "framer-motion";

export default function DiscoverPage() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const pathname = usePathname();

    const search = searchParams.get("search") || "";
    const category = searchParams.get("category") || "";
    const neighborhood = searchParams.get("neighborhood") || "";
    const risk = searchParams.get("risk") || "";

    const filteredBusinesses = useMemo(() => {
        return mockBusinesses.filter((b) => {
            const matchSearch =
                b.name.toLowerCase().includes(search.toLowerCase()) ||
                b.tagline.toLowerCase().includes(search.toLowerCase());
            const matchCategory = category ? b.category === category : true;
            const matchNeighborhood = neighborhood ? b.neighborhood === neighborhood : true;
            const matchRisk = risk ? b.riskLevel === risk : true;

            return matchSearch && matchCategory && matchNeighborhood && matchRisk;
        });
    }, [search, category, neighborhood, risk]);

    const handleClearFilters = () => {
        router.push(pathname);
    };

    return (
        <main className="min-h-screen bg-white">
            <div className="max-w-[1600px] mx-auto px-6 md:px-12 pb-20">
                <DirectoryHeader />

                <FilterBar />

                {/* Grid */}
                <motion.div
                    layout
                    className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-x-6 gap-y-10"
                >
                    <AnimatePresence>
                        {filteredBusinesses.map((business, index) => (
                            <motion.div
                                layout
                                key={business.id}
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                transition={{ duration: 0.3 }}
                            >
                                <BusinessCard business={business} />
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </motion.div>

                {filteredBusinesses.length === 0 && (
                    <div className="w-full text-center py-32 opacity-60">
                        <h3 className="text-xl font-semibold mb-2 text-gray-900">No businesses found</h3>
                        <p className="text-gray-500">Try adjusting your filters or search terms.</p>
                        <button
                            className="mt-6 px-6 py-2 border border-black rounded-lg hover:bg-gray-50 transition-colors font-medium text-sm"
                            onClick={handleClearFilters}
                        >
                            Clear all filters
                        </button>
                    </div>
                )}
            </div>
        </main>
    );
}
