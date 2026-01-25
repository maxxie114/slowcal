"use client";

import { useState, useMemo, useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap, useMapEvents } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { Business } from "@/lib/types";
import { MapPreviewCard } from "@/components/directory/MapPreviewCard";
import L from "leaflet";
import { renderToStaticMarkup } from "react-dom/server";
import { MapMarker } from "@/components/directory/MapMarker";

// Fix for default marker icons in Next.js/Leaflet
const DefaultIcon = L.icon({
    iconUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png',
    shadowUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

interface BusinessMapProps {
    businesses: Business[];
}

function MapController() {
    const map = useMap();

    useEffect(() => {
        // Invalidate size to ensure map renders correctly after load
        map.invalidateSize();
    }, [map]);

    return null;
}

function MapClickHandler({ onClick }: { onClick: () => void }) {
    useMapEvents({
        click: () => {
            onClick();
        },
    });
    return null;
}

export function BusinessMap({ businesses }: BusinessMapProps) {
    const [selectedBusinessId, setSelectedBusinessId] = useState<string | null>(null);

    const selectedBusiness = useMemo(
        () => businesses.find((b) => b.id === selectedBusinessId),
        [businesses, selectedBusinessId]
    );

    const validBusinesses = useMemo(
        () => businesses.filter((b) => b.lat && b.lng),
        [businesses]
    );

    const createCustomIcon = (business: Business, isSelected: boolean) => {
        // Create a synthetic marker using the existing React component
        const markerHtml = renderToStaticMarkup(
            <div className={`transition-transform duration-300 ${isSelected ? 'scale-110' : 'hover:scale-110'}`}>
                <MapMarker
                    riskLevel={business.riskLevel}
                    isSelected={isSelected}
                />
            </div>
        );

        return L.divIcon({
            html: markerHtml,
            className: '!bg-transparent !border-none', // Override Leaflet defaults
            iconSize: isSelected ? [32, 32] : [24, 24],
            iconAnchor: isSelected ? [16, 16] : [12, 12],
            popupAnchor: [0, -12]
        });
    };

    return (
        <div className="w-full h-[600px] rounded-xl overflow-hidden shadow-sm border border-gray-200 relative z-0">
            <MapContainer
                center={[37.7577, -122.4376]}
                zoom={12}
                style={{ height: "100%", width: "100%" }}
                scrollWheelZoom={true}
            >
                <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                    url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                />

                <MapController />
                <MapClickHandler onClick={() => setSelectedBusinessId(null)} />

                {validBusinesses.map((business) => (
                    <Marker
                        key={business.id}
                        position={[business.lat, business.lng]}
                        icon={createCustomIcon(business, selectedBusinessId === business.id)}
                        eventHandlers={{
                            click: () => setSelectedBusinessId(business.id),
                        }}
                    >
                        {selectedBusinessId === business.id && (
                            <Popup
                                closeButton={false}
                                className="custom-popup bg-transparent shadow-none border-none"
                                minWidth={300}
                                maxWidth={300}
                            >
                                <div onClick={(e) => e.stopPropagation()}>
                                    <MapPreviewCard business={business} />
                                </div>
                            </Popup>
                        )}
                    </Marker>
                ))}
            </MapContainer>
        </div>
    );
}
