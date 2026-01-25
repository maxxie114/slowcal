"use client";

import { RiskLevel } from "@/lib/types";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";

interface MapMarkerProps {
    riskLevel: RiskLevel;
    onClick?: () => void;
    isSelected?: boolean;
}

export function MapMarker({ riskLevel, onClick, isSelected }: MapMarkerProps) {
    const getColor = (level: RiskLevel) => {
        switch (level) {
            case "low":
                return "bg-[#84A98C]"; // Sage Green
            case "moderate":
                return "bg-[#F4A261]"; // Amber/Orange-ish (adjusting to match description)
            case "high":
            case "critical":
                return "bg-[#E76F51]"; // Burnt Red
            default:
                return "bg-gray-500";
        }
    };

    return (
        <motion.button
            whileHover={{ scale: 1.2 }}
            whileTap={{ scale: 0.9 }}
            onClick={onClick}
            className={cn(
                "relative w-6 h-6 rounded-full border-2 border-white shadow-md cursor-pointer flex items-center justify-center transition-all duration-300",
                getColor(riskLevel),
                isSelected ? "w-8 h-8 z-20 ring-2 ring-black ring-offset-2" : "z-10 opacity-90 hover:opacity-100 hover:z-20"
            )}
        >
            {/* Inner dot for detail */}
            <div className="w-1.5 h-1.5 bg-white rounded-full opacity-80" />
        </motion.button>
    );
}
