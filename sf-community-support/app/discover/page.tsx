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
    const riskParam = searchParams.get("risk") || "";
    
    const [businesses, setBusinesses] = useState<Business[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const perPage = 50;
    const [totalCount, setTotalCount] = useState<number>(0);

    useEffect(() => {
        async function fetchBusinesses() {
            setLoading(true);
            console.log('Fetching businesses (page)', page);

            // Determine if we should apply a risk-level filter from the URL (e.g. ?risk=high)
            const normalizeRisk = (r: string) => {
                if (!r) return null;
                const s = r.toString().toLowerCase();
                // map UI synonyms to DB-friendly tokens
                if (s === 'critical') return 'high'; // DB uses 'High' not 'Critical'
                if (s === 'moderate') return 'medium';
                if (['high','medium','low'].includes(s)) return s;
                return null;
            };

            const riskFilter = normalizeRisk(riskParam);

            // Build count query with optional filters
            let countQuery: any = supabase
                .from('master_model_data')
                .select('*', { count: 'exact', head: true });
            if (riskFilter) countQuery = countQuery.ilike('risk_level', riskFilter);
            if (neighborhood) countQuery = countQuery.eq('neighborhood', neighborhood);

            const { count, error: countError } = await countQuery;

            if (countError) {
                console.error('Error counting businesses:', countError);
            }
            const safeCount = typeof count === 'number' ? count : 0;
            setTotalCount(safeCount);

            const from = (page - 1) * perPage;
            const to = from + perPage - 1;

            // Build data query with same optional filters
            let dataQuery: any = supabase
                .from('master_model_data')
                .select('*')
                .order('id', { ascending: true })
                .range(from, to);
            if (riskFilter) dataQuery = dataQuery.ilike('risk_level', riskFilter);
            if (neighborhood) dataQuery = dataQuery.eq('neighborhood', neighborhood);

            const { data, error } = await dataQuery;

            if (error) {
                console.error('Error fetching businesses:', error);
                setBusinesses([]);
                setLoading(false);
                return;
            }

            console.log('Fetched data length:', data?.length);

            // Small, fast deterministic SVG generator for mock photos based on business name.
            const generatePlaceholder = (name: string, w = 800, h = 600) => {
                const safe = (name || "").toString();
                const initials = safe.split(/\s+/).slice(0,2).map(s => s[0]?.toUpperCase() || "").join("") || "BB";
                // simple hash to pick a background color
                let hash = 0;
                for (let i = 0; i < safe.length; i++) hash = (hash << 5) - hash + safe.charCodeAt(i) | 0;
                const colors = ["#F59E0B","#EF4444","#06B6D4","#10B981","#8B5CF6","#F472B6","#F97316","#3B82F6"];
                const bg = colors[Math.abs(hash) % colors.length];
                const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='${w}' height='${h}' viewBox='0 0 ${w} ${h}'>` +
                    `<rect width='100%' height='100%' fill='${bg}'/>` +
                    `<text x='50%' y='50%' dy='.35em' text-anchor='middle' font-family='Inter, Arial, sans-serif' font-size='${Math.round(Math.min(w,h)/6)}' fill='#fff' font-weight='700'>${initials}</text>` +
                    `</svg>`;
                return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
            };

            const detectCategory = (item: any) => {
                const name = (item.dba_name || item.ownership_name || "").toString().toLowerCase();
                const desc = (item.naic_code_description || "").toString().toLowerCase();
                // Simple keyword-based mapping. Maintain this list in-code as requested.
                if (/food|restaurant|dining|cafe|coffee|bakery|bar|pizza|bistro/.test(name) || /food|restaurant|cafe|bakery/.test(desc)) return 'restaurant';
                if (/cafe|coffee|espresso|tea/.test(name) || /cafe/.test(desc)) return 'cafe';
                if (/retail|store|shop|boutique|grocery|market/.test(name) || /retail|grocery|store/.test(desc)) return 'retail';
                if (/book|bookstore|books/.test(name) || /bookstore/.test(desc)) return 'bookstore';
                if (/service|services|contractor|plumb|electric|repair|construction/.test(name) || /services|construction/.test(desc)) return 'services';
                if (/grocery|market|produce|supermarket/.test(name) || /grocery|market/.test(desc)) return 'grocery';
                return 'other';
            };

            const generateCategoryPlaceholder = (category: string, name: string, desc = '', w = 800, h = 600) => {
                // Keyword -> image pools for better relevance. If a keyword is found in the name/desc,
                // pick from that keyword's pool; otherwise fall back to category pool.
                const KEYWORD_POOLS: Record<string, string[]> = {
                    pizza: [
                        'https://images.unsplash.com/photo-1606756792635-8b6f4a5f6b9a',
                        'https://images.unsplash.com/photo-1548365328-6a2f28f0c83a'
                    ],
                    sushi: [
                        'https://images.unsplash.com/photo-1546069901-ba9599a7e63c',
                        'https://images.unsplash.com/photo-1553621042-f6e147245754'
                    ],
                    taco: [
                        'https://images.unsplash.com/photo-1604908177522-1a7a2a6e3f90'
                    ],
                    coffee: [
                        'https://images.unsplash.com/photo-1509042239860-f550ce710b93',
                        'https://images.unsplash.com/photo-1504754524776-8f4f37790ca0'
                    ],
                    bakery: [
                        'https://images.unsplash.com/photo-1504674900247-0877df9cc836'
                    ],
                    bar: [
                        'https://images.unsplash.com/photo-1504674900247-0877df9cc836'
                    ],
                    book: [
                        'https://images.unsplash.com/photo-1519681393784-d120267933ba'
                    ],
                    salon: [
                        'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9'
                    ],
                    plumbing: [
                        'https://images.unsplash.com/photo-1581579181167-3b2b2a3bcd6a'
                    ],
                    grocery: [
                        'https://images.unsplash.com/photo-1466637574441-749b8f19452f',
                        'https://images.unsplash.com/photo-1543352634-8f6b9cb3f3d2'
                    ]
                };

                const IMAGE_POOLS: Record<string, string[]> = {
                    restaurant: [
                        'https://images.unsplash.com/photo-1541542684-67b5f5f4b86d',
                        'https://images.unsplash.com/photo-1473093226795-af9932fe5856',
                        'https://images.unsplash.com/photo-1414235077428-338989a2e8c0'
                    ],
                    cafe: [
                        'https://images.unsplash.com/photo-1504754524776-8f4f37790ca0',
                        'https://images.unsplash.com/photo-1459257868276-5e65389e2722',
                        'https://images.unsplash.com/photo-1509042239860-f550ce710b93'
                    ],
                    retail: [
                        'https://images.unsplash.com/photo-1423784346385-c1d4dac9893a',
                        'https://images.unsplash.com/photo-1441984904996-e0b6ba687e04',
                        'https://images.unsplash.com/photo-1484981184820-2e84ea0e4b04'
                    ],
                    bookstore: [
                        'https://images.unsplash.com/photo-1519681393784-d120267933ba',
                        'https://images.unsplash.com/photo-1512820790803-83ca734da794',
                        'https://images.unsplash.com/photo-1495446815901-a7297e633e8d'
                    ],
                    services: [
                        'https://images.unsplash.com/photo-1498050108023-c5249f4df085',
                        'https://images.unsplash.com/photo-1519389950473-47ba0277781c',
                        'https://images.unsplash.com/photo-1524758631624-e2822e304c36'
                    ],
                    grocery: [
                        'https://images.unsplash.com/photo-1543352634-8f6b9cb3f3d2',
                        'https://images.unsplash.com/photo-1466637574441-749b8f19452f',
                        'https://images.unsplash.com/photo-1435879211002-8f3f8b5b7f6f'
                    ],
                    other: [
                        'https://images.unsplash.com/photo-1521791136064-7986c2920216',
                        'https://images.unsplash.com/photo-1503602642458-232111445657',
                        'https://images.unsplash.com/photo-1487017159836-4e23ece2e4cf'
                    ]
                };

                const text = ((name || '') + ' ' + (desc || '')).toLowerCase();
                // find keyword match first
                for (const kw of Object.keys(KEYWORD_POOLS)) {
                    if (text.includes(kw)) {
                        const pool = KEYWORD_POOLS[kw];
                        let hash = 0;
                        for (let i = 0; i < text.length; i++) hash = (hash << 5) - hash + text.charCodeAt(i) | 0;
                        const idx = Math.abs(hash + kw.length) % pool.length;
                        return `${pool[idx]}?auto=format&fit=crop&w=${w}&q=60`;
                    }
                }

                const pool = IMAGE_POOLS[category] || IMAGE_POOLS.other;
                // deterministic pick based on name hash so images are stable per business
                let hash = 0;
                const s = (name || '').toString();
                for (let i = 0; i < s.length; i++) hash = (hash << 5) - hash + s.charCodeAt(i) | 0;
                const idx = Math.abs(hash) % pool.length;
                const raw = pool[idx];
                // add sizing and quality params to keep payload small
                return `${raw}?auto=format&fit=crop&w=${w}&q=60`;
            };

            const usedImages = new Set<string>();

            const pickImageForBusiness = (name: string, desc: string, category: string) => {
                // Try keyword pools first, then category pools. Ensure we pick an image not already used on the page
                const text = ((name || '') + ' ' + (desc || '')).toLowerCase();
                const tryPick = (pool: string[]) => {
                    if (!pool || pool.length === 0) return null;
                    // base deterministic index
                    let hash = 0;
                    const s = name + '|' + desc;
                    for (let i = 0; i < s.length; i++) hash = (hash << 5) - hash + s.charCodeAt(i) | 0;
                    const base = Math.abs(hash);
                    // try up to pool.length options to avoid repeats
                    for (let offset = 0; offset < pool.length; offset++) {
                        const idx = (base + offset) % pool.length;
                        const candidate = `${pool[idx]}?auto=format&fit=crop&w=800&q=60`;
                        if (!usedImages.has(candidate)) {
                            usedImages.add(candidate);
                            return candidate;
                        }
                    }
                    // if all used, return the base candidate (allow repeats as last resort)
                    const fallback = `${pool[base % pool.length]}?auto=format&fit=crop&w=800&q=60`;
                    return fallback;
                };

                // KEYWORD_POOLS and IMAGE_POOLS are in closure scope; reuse existing logic by reconstructing arrays.
                const KEYWORD_POOLS: Record<string, string[]> = {
                    pizza: [
                        'https://images.unsplash.com/photo-1606756792635-8b6f4a5f6b9a',
                        'https://images.unsplash.com/photo-1604908177522-1a7a2a6e3f90'
                    ],
                    sushi: [
                        'https://images.unsplash.com/photo-1546069901-ba9599a7e63c',
                        'https://images.unsplash.com/photo-1553621042-f6e147245754'
                    ],
                    taco: [
                        'https://images.unsplash.com/photo-1604908177522-1a7a2a6e3f90'
                    ],
                    coffee: [
                        'https://images.unsplash.com/photo-1509042239860-f550ce710b93',
                        'https://images.unsplash.com/photo-1504754524776-8f4f37790ca0'
                    ],
                    bakery: [
                        'https://images.unsplash.com/photo-1504674900247-0877df9cc836'
                    ],
                    bar: [
                        'https://images.unsplash.com/photo-1504674900247-0877df9cc836'
                    ],
                    book: [
                        'https://images.unsplash.com/photo-1519681393784-d120267933ba'
                    ],
                    salon: [
                        'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9'
                    ],
                    plumbing: [
                        'https://images.unsplash.com/photo-1581579181167-3b2b2a3bcd6a'
                    ],
                    grocery: [
                        'https://images.unsplash.com/photo-1466637574441-749b8f19452f',
                        'https://images.unsplash.com/photo-1543352634-8f6b9cb3f3d2'
                    ]
                };

                const IMAGE_POOLS: Record<string, string[]> = {
                    restaurant: [
                        'https://images.unsplash.com/photo-1541542684-67b5f5f4b86d',
                        'https://images.unsplash.com/photo-1473093226795-af9932fe5856',
                        'https://images.unsplash.com/photo-1414235077428-338989a2e8c0'
                    ],
                    cafe: [
                        'https://images.unsplash.com/photo-1504754524776-8f4f37790ca0',
                        'https://images.unsplash.com/photo-1459257868276-5e65389e2722',
                        'https://images.unsplash.com/photo-1509042239860-f550ce710b93'
                    ],
                    retail: [
                        'https://images.unsplash.com/photo-1423784346385-c1d4dac9893a',
                        'https://images.unsplash.com/photo-1441984904996-e0b6ba687e04',
                        'https://images.unsplash.com/photo-1484981184820-2e84ea0e4b04'
                    ],
                    bookstore: [
                        'https://images.unsplash.com/photo-1519681393784-d120267933ba',
                        'https://images.unsplash.com/photo-1512820790803-83ca734da794',
                        'https://images.unsplash.com/photo-1495446815901-a7297e633e8d'
                    ],
                    services: [
                        'https://images.unsplash.com/photo-1498050108023-c5249f4df085',
                        'https://images.unsplash.com/photo-1519389950473-47ba0277781c',
                        'https://images.unsplash.com/photo-1524758631624-e2822e304c36'
                    ],
                    grocery: [
                        'https://images.unsplash.com/photo-1543352634-8f6b9cb3f3d2',
                        'https://images.unsplash.com/photo-1466637574441-749b8f19452f',
                        'https://images.unsplash.com/photo-1435879211002-8f3f8b5b7f6f'
                    ],
                    other: [
                        'https://images.unsplash.com/photo-1521791136064-7986c2920216',
                        'https://images.unsplash.com/photo-1503602642458-232111445657',
                        'https://images.unsplash.com/photo-1487017159836-4e23ece2e4cf'
                    ]
                };

                // keyword match
                for (const kw of Object.keys(KEYWORD_POOLS)) {
                    if (text.includes(kw)) {
                        return tryPick(KEYWORD_POOLS[kw]);
                    }
                }

                return tryPick(IMAGE_POOLS[category] || IMAGE_POOLS.other);
            };

            const mappedBusinesses: Business[] = (data || []).map((item: any) => {
                const name = item.dba_name || item.ownership_name || "Unknown Business";
                const dbLevel = (item.risk_level || "").toString().toLowerCase();
                const allowed = ['critical', 'high', 'medium', 'moderate', 'low'];
                // Normalize riskLevel for display only (keep common synonyms)
                let riskLevel = 'low';
                if (allowed.includes(dbLevel)) {
                    if (dbLevel === 'moderate') riskLevel = 'medium';
                    else riskLevel = dbLevel;
                } else if (item.risk_score >= 0.5) {
                    riskLevel = 'high';
                }
                const cat = detectCategory(item);
                return ({
                    id: item.id?.toString?.() ?? String(item.id ?? ''),
                    name,
                    category: cat,
                    neighborhood: item.neighborhood ?? "",
                    address: item.full_business_address || "",
                    lat: 37.7749,
                    lng: -122.4194,
                    photoUrl: pickImageForBusiness(name, item.naic_code_description || '', cat),
                    riskScore: Math.round((item.risk_score || 0) * 100),
                    riskLevel: riskLevel,
                    tagline: item.naic_code_description || "Local Business",
                    story: "",
                    businessAge: item.business_age
                });
            });

            setBusinesses(mappedBusinesses);
            setLoading(false);
        }

        fetchBusinesses();
    }, [page, search, category, neighborhood, riskParam]);

    const filteredBusinesses = useMemo(() => {
        return businesses.filter((b) => {
            const term = search.toLowerCase();
            const nameText = (b.name || "").toString().toLowerCase();
            const taglineText = (b.tagline || "").toString().toLowerCase();
            const matchSearch = nameText.includes(term) || taglineText.includes(term);

            const matchNeighborhood = neighborhood ? b.neighborhood === neighborhood : true;

            const matchCategory = category ? b.category === category : true;

            return matchSearch && matchNeighborhood && matchCategory;
        });
    }, [search, neighborhood, businesses, category]);

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
