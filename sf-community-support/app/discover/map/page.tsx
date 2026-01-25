"use client";

import { useMemo, useEffect, useState } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { DirectoryHeader } from "@/components/directory/DirectoryHeader";
import { FilterBar } from "@/components/directory/FilterBar";
import dynamic from 'next/dynamic';
import { supabase } from "@/lib/supabase";
import { Business } from "@/lib/types";

const BusinessMap = dynamic(
    () => import('@/components/directory/BusinessMap').then((mod) => mod.BusinessMap),
    {
        ssr: false,
        loading: () => <div className="w-full h-[600px] bg-gray-100 animate-pulse rounded-xl flex items-center justify-center text-gray-400">Loading Map...</div>
    }
);

// Deterministic random number generator based on seed
function getPseudoRandom(seed: string) {
    let hash = 0;
    for (let i = 0; i < seed.length; i++) {
        const char = seed.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
    }
    const x = Math.sin(hash) * 10000;
    return x - Math.floor(x);
}

export default function MapPage() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const pathname = usePathname();

    const search = searchParams.get("search") || "";
    const category = searchParams.get("category") || "";
    const neighborhood = searchParams.get("neighborhood") || "";
    const risk = searchParams.get("risk") || "";

    const [businesses, setBusinesses] = useState<Business[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchBusinesses() {
            setLoading(true);
            
            // Fetch all high risk businesses for the map
            // We fetch all because the map needs to show clusters/distribution
            
            const { data, error } = await supabase
                .from('master_model_data')
                .select('*')
                .eq('risk_level', 'High');

            if (error) {
                console.error('Error fetching businesses for map:', error);
                setBusinesses([]);
                setLoading(false);
                return;
            }

            const mappedBusinesses: Business[] = (data || []).map((item: any) => {
                const idStr = item.id?.toString() || "0";
                // Generate synthetic coordinates if missing to spread them out on the map
                // SF bounds: Lat 37.71 to 37.80, Lng -122.50 to -122.38
                const latSeed = idStr + "lat";
                const lngSeed = idStr + "lng";
                
                const randomLat = 37.71 + (getPseudoRandom(latSeed) * (37.80 - 37.71));
                const randomLng = -122.50 + (getPseudoRandom(lngSeed) * (-122.38 - -122.50));

                return {
                    id: item.id?.toString?.() ?? String(item.id ?? ''),
                    name: item.dba_name || item.ownership_name || "Unknown Business",
                    category: 'other',
                    neighborhood: item.neighborhood || "Unknown Neighborhood",
                    address: item.full_business_address || "",
                    // Use actual coordinates if available, otherwise use synthetic ones
                    lat: item.latitude ? parseFloat(item.latitude) : randomLat,
                    lng: item.longitude ? parseFloat(item.longitude) : randomLng,
                    photoUrl: "https://images.unsplash.com/photo-1519167758481-83f550bb49b3?auto=format&fit=crop&q=80&w=800",
                    riskScore: Math.round((item.risk_score || 0) * 100),
                    riskLevel: item.risk_level?.toLowerCase?.() === 'high' ? 'high' : 'critical',
                    tagline: item.naic_code_description || "Local Business",
                    story: "",
                    businessAge: item.business_age
                };
            });

            // Filter out businesses that are just stuck at the default coordinate if we want a clean map,
            // but for now let's keep them so they show up at least.
            // Actually, if they all stack at the default, it's bad UX. 
            // The BusinessMap component filters validBusinesses by `b.lat && b.lng`.
            
            setBusinesses(mappedBusinesses);
            setLoading(false);
        }

        fetchBusinesses();
    }, []);

    const filteredBusinesses = useMemo(() => {
        return businesses.filter((b) => {
            const matchSearch =
                b.name.toLowerCase().includes(search.toLowerCase()) ||
                b.tagline.toLowerCase().includes(search.toLowerCase());
            
            // Map categories if possible, or just ignore if everything is 'other'
            const matchCategory = category ? b.category === category : true;
            
            const matchNeighborhood = neighborhood ? b.neighborhood === neighborhood : true;
            // Risk filter
            const matchRisk = risk ? b.riskLevel === risk : true;

            return matchSearch && matchNeighborhood && matchRisk; // Removed matchCategory for now as most are 'other'
        });
    }, [search, category, neighborhood, risk, businesses]);

    return (
        <main className="min-h-screen bg-white">
            <div className="max-w-[1600px] mx-auto px-6 md:px-12 pb-20">
                <DirectoryHeader />

                <FilterBar />

                {/* Map View */}
                <div className="w-full relative">
                    {loading && (
                        <div className="absolute inset-0 z-10 bg-white/50 flex items-center justify-center">
                            <div className="text-xl font-semibold">Loading Map Data...</div>
                        </div>
                    )}
                    <BusinessMap businesses={filteredBusinesses} />
                </div>
            </div>
        </main>
    );
}
