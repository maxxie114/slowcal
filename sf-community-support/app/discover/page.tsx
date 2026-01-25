"use client";

import { useMemo, useEffect, useState } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { DirectoryHeader } from "@/components/directory/DirectoryHeader";
import { FilterBar } from "@/components/directory/FilterBar";
import { BusinessCard } from "@/components/directory/BusinessCard";
import { motion, AnimatePresence } from "framer-motion";
import { supabase } from "@/lib/supabase";
import { Business } from "@/lib/types";

export default function DiscoverPage() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const pathname = usePathname();

    const search = searchParams.get("search") || "";
    const category = searchParams.get("category") || "";
    const neighborhood = searchParams.get("neighborhood") || "";
    // We ignore the risk param from URL for fetching, as we enforce 'High' risk
    
    const [businesses, setBusinesses] = useState<Business[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const perPage = 50;
    const [totalCount, setTotalCount] = useState<number>(0);

    useEffect(() => {
        async function fetchBusinesses() {
            setLoading(true);
            console.log('Fetching businesses (page)', page);

            const { count, error: countError } = await supabase
                .from('master_model_data')
                .select('*', { count: 'exact', head: true })
                .eq('risk_level', 'High');

            if (countError) {
                console.error('Error counting businesses:', countError);
            }
            const safeCount = typeof count === 'number' ? count : 0;
            setTotalCount(safeCount);

            const from = (page - 1) * perPage;
            const to = from + perPage - 1;

            const { data, error } = await supabase
                .from('master_model_data')
                .select('*')
                .eq('risk_level', 'High')
                .order('id', { ascending: true })
                .range(from, to);

            if (error) {
                console.error('Error fetching businesses:', error);
                setBusinesses([]);
                setLoading(false);
                return;
            }

            console.log('Fetched data length:', data?.length);

            const mappedBusinesses: Business[] = (data || []).map((item: any) => ({
                id: item.id?.toString?.() ?? String(item.id ?? ''),
                name: item.dba_name || item.ownership_name || "Unknown Business",
                category: 'other',
                neighborhood: item.neighborhood || "Unknown Neighborhood",
                address: item.full_business_address || "",
                lat: 37.7749,
                lng: -122.4194,
                photoUrl: "https://images.unsplash.com/photo-1519167758481-83f550bb49b3?auto=format&fit=crop&q=80&w=800",
                riskScore: Math.round((item.risk_score || 0) * 100),
                riskLevel: item.risk_level?.toLowerCase?.() === 'high' ? 'high' : 'critical',
                tagline: item.naic_code_description || "Local Business",
                story: "",
                businessAge: item.business_age
            }));

            setBusinesses(mappedBusinesses);
            setLoading(false);
        }

        fetchBusinesses();
    }, [page]);

    const filteredBusinesses = useMemo(() => {
        return businesses.filter((b) => {
            const matchSearch =
                b.name.toLowerCase().includes(search.toLowerCase()) ||
                b.tagline.toLowerCase().includes(search.toLowerCase());
            // We can still filter by category/neighborhood if the user selects them, 
            // but currently our category is always 'other' so that filter might hide everything if set to something else.
            // For now, we'll implement simple text filtering.
            
            const matchNeighborhood = neighborhood ? b.neighborhood === neighborhood : true;
            
            return matchSearch && matchNeighborhood;
        });
    }, [search, neighborhood, businesses]);

    const handleClearFilters = () => {
        router.push(pathname);
    };

    return (
        <main className="min-h-screen bg-white">
            <div className="max-w-[1600px] mx-auto px-6 md:px-12 pb-20">
                <DirectoryHeader />

                <FilterBar />

                {/* Grid */}
                {loading ? (
                     <div className="w-full text-center py-32 opacity-60">
                        <h3 className="text-xl font-semibold mb-2 text-gray-900">Loading businesses...</h3>
                    </div>
                ) : (
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
                )}

                {!loading && totalCount > 0 && (
                    <div className="mt-10 flex flex-col sm:flex-row items-center justify-between gap-4">
                        <div className="text-sm text-gray-600">
                            Showing {Math.min((page - 1) * perPage + 1, totalCount)}–{Math.min(page * perPage, totalCount)} of {totalCount}
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                className="px-3 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-40"
                                disabled={page <= 1}
                                onClick={() => setPage((p) => Math.max(1, p - 1))}
                            >
                                Previous
                            </button>
                            <span className="text-sm text-gray-700 px-2">
                                Page {page} of {Math.max(1, Math.ceil(totalCount / perPage))}
                            </span>
                            <button
                                className="px-3 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-40"
                                disabled={page >= Math.ceil(totalCount / perPage)}
                                onClick={() => setPage((p) => p + 1)}
                            >
                                Next
                            </button>
                        </div>
                    </div>
                )}

                {!loading && filteredBusinesses.length === 0 && (
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
