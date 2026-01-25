import Link from "next/link";
import { Business } from "@/lib/types";
import { RiskIndicator } from "@/components/ui/RiskIndicator";
import { Star, Heart } from "lucide-react";

interface BusinessCardProps {
    business: Business;
}

export function BusinessCard({ business }: BusinessCardProps) {
    const generateFallback = (business: Business) => {
        const emojiMap: Record<string,string> = {
            restaurant: '🍽️',
            cafe: '☕',
            retail: '🛍️',
            bookstore: '📚',
            services: '🛠️',
            grocery: '🥦',
            other: '🏬'
        };
        const bgMap: Record<string,string> = {
            restaurant: '#F97316',
            cafe: '#EF4444',
            retail: '#3B82F6',
            bookstore: '#8B5CF6',
            services: '#10B981',
            grocery: '#F59E0B',
            other: '#64748B'
        };
        const emoji = emojiMap[business.category] || '🏬';
        const bg = bgMap[business.category] || '#64748B';
        const label = (business.name || '').split(' ').slice(0,2).join(' ');
        const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='800' height='600' viewBox='0 0 800 600'>` +
            `<rect width='100%' height='100%' fill='${bg}'/>` +
            `<text x='50%' y='45%' text-anchor='middle' font-family='Inter, Arial, sans-serif' font-size='96' fill='#fff'>${emoji}</text>` +
            `<text x='50%' y='85%' text-anchor='middle' font-family='Inter, Arial, sans-serif' font-size='26' fill='#fff'>${label}</text>` +
            `</svg>`;
        return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
    };
    return (
        <Link href={`/business/${business.id}`} className="group flex flex-col gap-3 cursor-pointer">
            {/* Image Container */}
            <div className="relative aspect-[20/19] w-full overflow-hidden rounded-xl bg-gray-200">
                {/* Heart Icon (Wishlist) */}
                <div className="absolute top-3 right-3 z-10 transition-transform active:scale-90">
                    <Heart className="w-6 h-6 text-white opacity-70 hover:opacity-100 hover:fill-white/50 transition-all stroke-[2px]" />
                </div>

                {/* Image */}
                <img
                    src={business.photoUrl}
                    alt={business.name}
                    className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                    loading="lazy"
                    decoding="async"
                    onError={(e) => {
                        const t = e.currentTarget as HTMLImageElement;
                        t.onerror = null;
                        t.src = generateFallback(business);
                    }}
                />

                {/* Risk Badge (Overlay) */}
                {business.riskLevel === 'critical' || business.riskLevel === 'high' ? (
                    <div className="absolute top-3 left-3 bg-white/90 backdrop-blur-sm px-2 py-1 rounded-md shadow-sm">
                        <span className="text-xs font-bold uppercase tracking-wider text-red-600">
                            {business.riskLevel} Risk
                        </span>
                    </div>
                ) : null}
            </div>

            {/* Content */}
            <div className="flex flex-col gap-1">
                <div className="flex justify-between items-start">
                    <h3 className="font-semibold text-gray-900 group-hover:underline decoration-1 underline-offset-2 decoration-gray-900 line-clamp-1">
                        {business.name}
                    </h3>
                    <div className="flex items-center gap-1 text-sm">
                        <Star className="w-3.5 h-3.5 fill-black text-black" />
                        <span>{(4 + Math.random()).toFixed(2)}</span>
                    </div>
                </div>

                <p className="text-gray-500 text-sm line-clamp-1">
                    {business.neighborhood}
                </p>
                {business.address && (
                    <p className="text-gray-400 text-xs line-clamp-1">
                        {business.address}
                    </p>
                )}

                <p className="text-gray-500 text-sm line-clamp-1 mt-1">
                    {business.tagline}
                </p>
                
                {business.businessAge ? (
                    <p className="text-xs text-gray-400">
                        {business.businessAge} years in business
                    </p>
                ) : null}

                <div className="mt-2 flex items-baseline gap-1">
                    <span className="font-semibold text-black">
                        {business.riskScore}%
                    </span>
                    <span className="text-gray-900 text-sm">risk score</span>
                </div>
            </div>
        </Link>
    );
}
