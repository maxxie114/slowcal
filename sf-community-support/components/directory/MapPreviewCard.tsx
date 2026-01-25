"use client";

import { Business } from "@/lib/types";
import Link from "next/link";
import { ArrowRight, Star } from "lucide-react";

interface MapPreviewCardProps {
    business: Business;
}

export function MapPreviewCard({ business }: MapPreviewCardProps) {
    return (
        <Link href={`/business/${business.id}`} className="block w-[240px] bg-[#fdfbf7] rounded-lg shadow-xl overflow-hidden border border-gray-200">
            {/* Image */}
            <div className="relative h-28 w-full overflow-hidden">
                <img
                    src={business.photoUrl}
                    alt={business.name}
                    className="w-full h-full object-cover"
                />
                {/* Tape Overlay Effect */}
                <div className="absolute top-[-10px] left-[50%] translate-x-[-50%] w-20 h-6 bg-[#f0e6ce] opacity-80 rotate-[-2deg] shadow-sm transform z-10" />

                {/* Risk Badge */}
                <div className="absolute top-2 right-2 bg-white/90 backdrop-blur-sm px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider text-black">
                    {business.riskLevel} Risk
                </div>
            </div>

            {/* Content */}
            <div className="p-3">
                <h3 className="font-semibold text-gray-900 leading-tight mb-1 truncate">
                    {business.name}
                </h3>

                <div className="flex items-center gap-1 text-xs text-gray-600 mb-2">
                    <span>{business.neighborhood}</span>
                    <span>•</span>
                    <span className="capitalize">{business.category}</span>
                </div>

                <div className="flex items-center justify-between mt-2">
                    <div className="flex items-center gap-1 text-xs font-medium">
                        <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                        <span>{(4 + Math.random()).toFixed(1)}</span>
                    </div>

                    <div className="text-xs font-medium bg-black text-white px-2 py-1 rounded-full flex items-center gap-1 group">
                        View
                        <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                    </div>
                </div>
            </div>
        </Link>
    );
}
