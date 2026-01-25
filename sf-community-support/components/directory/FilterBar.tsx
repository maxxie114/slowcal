import { Search, SlidersHorizontal, Utensils, Coffee, ShoppingBag, BookOpen, Wrench, Apple, Infinity, ChevronDown } from "lucide-react";
import { useCallback } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const CATEGORIES = [
    { id: "", label: "All", icon: null },
    { id: "restaurant", label: "Restaurant", icon: Utensils },
    { id: "cafe", label: "Cafe", icon: Coffee },
    { id: "retail", label: "Retail", icon: ShoppingBag },
    { id: "bookstore", label: "Bookstore", icon: BookOpen },
    { id: "services", label: "Services", icon: Wrench },
    { id: "grocery", label: "Grocery", icon: Apple },
];

const NEIGHBORHOODS = [
    "Alamo Square", "Anza Vista", "Ashbury Heights", "Balboa Park", "Balboa Terrace", "Bayview", "Bernal Heights", "Castro", "Cathedral Hill", "Cayuga Terrace",
    "Chinatown", "Civic Center", "Clarendon Heights", "Cole Valley", "Corona Heights", "Cow Hollow", "Crocker-Amazon", "Diamond Heights", "Dogpatch", "Dolores Heights",
    "Duboce Triangle", "Embarcadero", "Eureka Valley", "Excelsior", "Fillmore", "Financial District", "Fisherman's Wharf", "Forest Hill", "Forest Knolls", "Glen Park",
    "Golden Gate Heights", "Haight-Ashbury", "Hayes Valley", "Hunters Point", "Ingleside", "Ingleside Heights", "Ingleside Terraces", "Inner Richmond", "Inner Sunset",
    "Japantown", "Lakeshore", "Lakeside", "Laurel Heights", "Little Hollywood", "Little Russia", "Marina", "Merced Heights", "Merced Manor", "Midtown Terrace",
    "Miraloma Park", "Mission Bay", "Mission District", "Mission Dolores", "Mission Terrace", "Monterey Heights", "Mount Davidson Manor", "Nob Hill", "Noe Valley",
    "North Beach", "North Panhandle", "Oceanview", "Outer Mission", "Outer Richmond", "Outer Sunset", "Pacific Heights", "Parkmerced", "Parkside", "Polk Gulch",
    "Portola", "Potrero Hill", "Presidio", "Presidio Heights", "Richmond District", "Rincon Hill", "Russian Hill", "Saint Francis Wood", "Sea Cliff", "Sherwood Forest",
    "Silver Terrace", "South Beach", "South of Market (SoMa)", "St. Mary's Park", "Stonestown", "Sunnydale", "Sunnyside", "Sunset District", "Telegraph Hill",
    "Tenderloin", "Treasure Island", "Twin Peaks", "Union Square", "University Mound", "Upper Market", "Visitacion Valley", "West Portal", "West of Twin Peaks",
    "Western Addition", "Westwood Highlands", "Westwood Park", "Yerba Buena"
].sort();

export function FilterBar() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const pathname = usePathname();

    const createQueryString = useCallback(
        (name: string, value: string) => {
            const params = new URLSearchParams(searchParams.toString());
            if (value) {
                params.set(name, value);
            } else {
                params.delete(name);
            }
            return params.toString();
        },
        [searchParams]
    );

    const handleSearchChange = (value: string) => {
        router.push(pathname + "?" + createQueryString("search", value));
    };

    const handleCategoryClick = (categoryId: string) => {
        router.push(pathname + "?" + createQueryString("category", categoryId));
    };

    const handleNeighborhoodChange = (value: string) => {
        router.push(pathname + "?" + createQueryString("neighborhood", value));
    };

    const handleRiskChange = (value: string) => {
        router.push(pathname + "?" + createQueryString("risk", value));
    };

    const currentCategory = searchParams.get("category") || "";
    const currentSearch = searchParams.get("search") || "";
    const currentNeighborhood = searchParams.get("neighborhood") || "";
    const currentRisk = searchParams.get("risk") || "";

    return (
        <div className="w-full flex flex-col gap-6 mb-8">
            {/* Top Row: Search & Filter Button */}
            <div className="flex items-center justify-center w-full max-w-3xl mx-auto gap-4">
                <div className="relative flex-grow shadow-md rounded-full hover:shadow-lg transition-shadow duration-300">
                    <div className="flex items-center bg-white rounded-full border border-gray-200 lg:min-w-[400px]">
                        <div className="pl-6 py-3">
                            <Search className="w-5 h-5 text-gray-500" />
                        </div>
                        <input
                            type="text"
                            placeholder="Start your search"
                            className="bg-transparent border-none focus:outline-none focus:ring-0 w-full py-3 px-4 text-sm font-medium placeholder:text-gray-500 text-gray-900"
                            defaultValue={currentSearch}
                            onChange={(e) => handleSearchChange(e.target.value)}
                        />
                        <div className="pr-2">
                            <div className="bg-accent-orange p-2 rounded-full text-white cursor-pointer hover:bg-orange-600 transition-colors">
                                <Search className="w-4 h-4" />
                            </div>
                        </div>
                    </div>
                </div>

                {/* Simple Filter Dropdowns */}
                <div className="hidden md:flex gap-2">
                    <div className="relative group">
                        <select
                            className="appearance-none bg-white border border-gray-300 rounded-full px-4 py-2 text-sm font-medium text-gray-700 hover:border-black cursor-pointer focus:outline-none transition-colors pr-8 w-40"
                            value={currentNeighborhood}
                            onChange={(e) => handleNeighborhoodChange(e.target.value)}
                        >
                            <option value="">Anywhere</option>
                            {NEIGHBORHOODS.map((neighborhood) => (
                                <option key={neighborhood} value={neighborhood}>
                                    {neighborhood}
                                </option>
                            ))}
                        </select>
                         <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
                    </div>

                    <div className="relative group">
                        <select
                        className="appearance-none bg-white border border-gray-300 rounded-full px-4 py-2 text-sm font-medium text-gray-700 hover:border-black cursor-pointer focus:outline-none transition-colors"
                        value={currentRisk}
                        onChange={(e) => handleRiskChange(e.target.value)}
                    >
                        <option value="">Any Risk</option>
                        <option value="critical">Critical</option>
                        <option value="high">High</option>
                        <option value="moderate">Moderate</option>
                        <option value="low">Low</option>
                    </select>
                </div>
                </div>

                <button className="md:hidden p-3 border border-gray-300 rounded-full hover:bg-gray-50 bg-white">
                    <SlidersHorizontal className="w-4 h-4 text-gray-700" />
                </button>
            </div>

            {/* Bottom Row: Categories Carousel */}
            <div className="w-full border-t border-gray-200 pt-6">
                <div className="flex gap-8 overflow-x-auto pb-4 no-scrollbar items-center justify-start md:justify-center w-full px-4">
                    {CATEGORIES.map((cat) => {
                        const Icon = cat.icon;
                        const isActive = currentCategory === cat.id;
                        return (
                            <button
                                key={cat.id || "all"}
                                onClick={() => handleCategoryClick(cat.id)}
                                className={cn(
                                    "flex flex-col items-center gap-2 min-w-[64px] cursor-pointer group transition-all duration-300 border-b-2 pb-2",
                                    isActive
                                        ? "border-black opacity-100"
                                        : "border-transparent opacity-60 hover:opacity-80 hover:border-gray-300"
                                )}
                            >
                                {Icon ? (
                                    <Icon className={cn("w-6 h-6", isActive ? "text-black" : "text-gray-500")} />
                                ) : (
                                    <Infinity className={cn("w-6 h-6", isActive ? "text-black" : "text-gray-500")} />
                                )}
                                <span className={cn("text-xs font-medium whitespace-nowrap", isActive ? "text-black" : "text-gray-500")}>
                                    {cat.label}
                                </span>
                            </button>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
