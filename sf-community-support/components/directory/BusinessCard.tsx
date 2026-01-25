import Link from "next/link";
import { Business } from "@/lib/types";
import { RiskIndicator } from "@/components/ui/RiskIndicator";
import { Star, Heart } from "lucide-react";

interface BusinessCardProps {
    business: Business;
}

export function BusinessCard({ business }: BusinessCardProps) {
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
                    {business.neighborhood} · {business.category}
                </p>

                {/* Keep RiskIndicator for now as a more detailed view or replace? 
                     Airbnb shows price here. We could show 'Risk Score' or just a tagline.
                     Let's show the tagline as "Available dates" equivalent (gray text) 
                 */}
                <p className="text-gray-500 text-sm line-clamp-1">
                    {business.tagline}
                </p>

                <div className="mt-1 flex items-baseline gap-1">
                    <span className="font-semibold text-black">
                        {business.riskScore}%
                    </span>
                    <span className="text-gray-900 text-sm">risk score</span>
                </div>
            </div>
        </Link>
    );
}
