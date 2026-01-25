import Link from "next/link";
import { Grid, Map } from "lucide-react";
import { usePathname, useSearchParams } from "next/navigation";
import { cn } from "@/lib/utils";

export function DirectoryHeader() {
    const pathname = usePathname();
    const searchParams = useSearchParams();

    const isMapView = pathname?.includes("/map");
    const gridUrl = `/discover?${searchParams.toString()}`;
    const mapUrl = `/discover/map?${searchParams.toString()}`;

    return (
        <header className="w-full mb-6 pt-4">
            <div className="flex flex-col md:flex-row justify-between items-end md:items-center gap-4">
                <div>
                    {/* Clean minimalist logo/header */}
                    <Link href="/">
                        <h1 className="text-3xl font-script font-bold tracking-tight text-gray-900 hover:text-accent-orange transition-colors cursor-pointer">
                            SlowCal<span className="text-accent-orange">.</span>
                        </h1>
                    </Link>
                </div>

                <div className="flex bg-white rounded-lg p-1 border border-gray-200 shadow-sm">
                    <Link href={gridUrl}>
                        <button
                            className={cn(
                                "p-2 rounded hover:bg-gray-100 transition-all border border-transparent",
                                !isMapView ? "bg-white border-gray-100 text-black shadow-sm" : "text-gray-500"
                            )}
                        >
                            <Grid className="w-4 h-4" />
                        </button>
                    </Link>
                    <Link href={mapUrl}>
                        <button
                            className={cn(
                                "p-2 rounded hover:bg-gray-100 transition-all border border-transparent",
                                isMapView ? "bg-white border-gray-100 text-black shadow-sm" : "text-gray-500"
                            )}
                        >
                            <Map className="w-4 h-4" />
                        </button>
                    </Link>
                </div>
            </div>
        </header>
    );
}
