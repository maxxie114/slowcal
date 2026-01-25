"use client";

import { useMemo } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { DirectoryHeader } from "@/components/directory/DirectoryHeader";
import { FilterBar } from "@/components/directory/FilterBar";
import dynamic from 'next/dynamic';

const BusinessMap = dynamic(
    () => import('@/components/directory/BusinessMap').then((mod) => mod.BusinessMap),
    {
        ssr: false,
        loading: () => <div className="w-full h-[600px] bg-gray-100 animate-pulse rounded-xl flex items-center justify-center text-gray-400">Loading Map...</div>
    }
);

import { mockBusinesses } from "@/lib/mockData";

export default function MapPage() {
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

    return (
        <main className="min-h-screen bg-white">
            <div className="max-w-[1600px] mx-auto px-6 md:px-12 pb-20">
                <DirectoryHeader />

                <FilterBar />

                {/* Map View */}
                <div className="w-full">
                    <BusinessMap businesses={filteredBusinesses} />
                </div>
            </div>
        </main>
    );
}
