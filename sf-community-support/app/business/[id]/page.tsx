import { ArrowLeft, MapPin, Clock, Navigation, Star } from "lucide-react";
import Link from "next/link";
import { PolaroidImage } from "@/components/ui/PolaroidImage";
import { RiskIndicator } from "@/components/ui/RiskIndicator";
import { TapeStrip } from "@/components/ui/TapeStrip";
import { cn } from "@/lib/utils";
import { mockBusinesses } from "@/lib/mockData";
import { notFound } from "next/navigation";

export default function BusinessProfilePage({ params }: { params: { id: string } }) {
    const business = mockBusinesses.find(b => b.id === params.id);

    if (!business) {
        return notFound();
    }

    // Default data for fields not in the main data source yet
    const tags = [business.category, business.neighborhood, "Local Favorite"];
    const riskReason = business.riskLevel === 'critical' 
        ? "Facing immediate displacement pressure due to significant rent increases."
        : business.riskLevel === 'high'
        ? "Lease renewal coming up with expected rate hikes."
        : business.riskLevel === 'moderate'
        ? "Steady business but operating on thin margins."
        : "Currently stable but needs community support to thrive.";
    
    const hours = "Open Daily: 10:00 AM - 7:00 PM";
    
    // Use the tagline as the intro to the story if story is missing
    const story = business.story || `
        ${business.tagline}
        
        ${business.name} has been a staple of the ${business.neighborhood} community. We take pride in serving our neighbors and visitors alike.
        
        "We love this neighborhood," says the owner. "It's our home, and we want to keep serving our community for years to come."
        
        Your support helps us keep our doors open and our traditions alive.
    `;

    // Default reviews
    const reviews = [
        { id: 1, user: "Alex M.", rating: 5, date: "2 days ago", text: "Such a gem! I love coming here." },
        { id: 2, user: "Jamie L.", rating: 5, date: "1 week ago", text: "Great service and amazing quality. Highly recommend." },
        { id: 3, user: "Sam K.", rating: 4, date: "2 weeks ago", text: "A classic spot in the neighborhood. Always reliable." },
    ];

    // Ensure we have 3 images for the gallery
    const displayImages = business.gallery && business.gallery.length >= 3 
        ? business.gallery.slice(0, 3) 
        : [
            { src: business.photoUrl, alt: business.name, caption: "Storefront" },
            { src: business.photoUrl, alt: business.name, caption: "Interior" },
            { src: business.photoUrl, alt: business.name, caption: "Details" }
        ];

    return (
        <main className="min-h-screen pb-32 bg-paper-cream">
            {/* Navigation */}
            <div className="p-4 md:p-6">
                <Link href="/discover" className="inline-flex items-center text-ink-light hover:text-ink-medium transition-colors">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Map
                </Link>
            </div>

            <div className="max-w-4xl mx-auto px-4 md:px-8">
                {/* Gallery Section */}
                <div className="relative py-8 md:py-12 mb-8">
                    <div className="flex flex-col md:flex-row items-center justify-center gap-8 md:gap-12 pl-4">
                        {displayImages.map((img, idx) => (
                            <div key={idx} className={cn(
                                "transition-transform hover:z-20",
                                idx === 0 && "-rotate-6 md:-translate-x-4",
                                idx === 1 && "rotate-3 z-10",
                                idx === 2 && "-rotate-3 md:translate-x-4",
                            )}>
                                <PolaroidImage
                                    src={img.src}
                                    alt={img.alt}
                                    caption={img.caption}
                                    rotation="none" // We handle rotation in parent for the composition
                                    className="w-full h-full object-cover"
                                    fill
                                />
                            </div>
                        ))}
                    </div>
                </div>

                {/* Header Info */}
                <div className="text-center mb-12 relative">
                    <h1 className="font-script text-5xl md:text-6xl text-ink-dark mb-6 transform -rotate-1 relative z-10 inline-block">
                        {business.name}
                    </h1>

                    <div className="flex flex-wrap justify-center gap-3 mb-6">
                        {tags.map((tag, i) => (
                            <span key={tag} className={cn(
                                "px-4 py-1.5 bg-paper-white border border-stone-200 shadow-sm text-sm font-medium text-ink-medium transform",
                                i % 2 === 0 ? "rotate-1" : "-rotate-1"
                            )}>
                                {tag}
                            </span>
                        ))}
                    </div>

                    <div className="inline-flex flex-col items-center bg-paper-white/50 p-4 rounded-xl backdrop-blur-sm border border-stone-100">
                        <RiskIndicator level={business.riskLevel} className="mb-2" />
                        <p className="text-xs text-ink-light max-w-xs mx-auto leading-relaxed">
                            {riskReason}
                        </p>
                    </div>
                </div>

                {/* Story Section */}
                <div className="relative max-w-2xl mx-auto mb-16">
                    <TapeStrip variant="corner-tl" className="-left-4 -top-4 w-32 opacity-80" />
                    <TapeStrip variant="corner-br" className="-right-4 -bottom-4 w-32 opacity-80" />

                    <div className="bg-paper-white p-8 md:p-12 shadow-paper rotate-[0.5deg]">
                        <h2 className="font-script text-3xl text-ink-medium mb-6">Our Story</h2>
                        <div className="prose prose-stone prose-lg font-serif leading-relaxed text-ink-medium">
                            {story.split('\n').map((paragraph, i) => (
                                paragraph.trim() && <p key={i} className="mb-4">{paragraph}</p>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Reviews Section */}
                <div className="max-w-2xl mx-auto mb-20">
                    <h3 className="font-script text-2xl text-ink-light mb-6 text-center">Community Love</h3>
                    <div className="space-y-4">
                        {reviews.map((review) => (
                            <div key={review.id} className="bg-white/60 p-4 rounded-lg border border-stone-100/50">
                                <div className="flex justify-between items-start mb-2">
                                    <div className="flex items-center gap-2">
                                        <span className="font-semibold text-ink-medium">{review.user}</span>
                                        <div className="flex text-yellow-500">
                                            {[...Array(5)].map((_, i) => (
                                                <Star key={i} size={12} fill={i < review.rating ? "currentColor" : "none"} className={i >= review.rating ? "text-stone-300" : ""} />
                                            ))}
                                        </div>
                                    </div>
                                    <span className="text-xs text-stone-400">{review.date}</span>
                                </div>
                                <p className="text-sm text-ink-medium italic">"{review.text}"</p>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Sticky Bottom Actions */}
            <div className="fixed bottom-0 left-0 right-0 bg-white/95 backdrop-blur-md border-t border-stone-200 p-4 shadow-lg-up z-50">
                <div className="max-w-4xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
                    <div className="flex flex-col md:flex-row gap-4 md:gap-8 text-sm text-ink-medium">
                        <div className="flex items-center gap-2">
                            <MapPin className="w-4 h-4 text-risk-medium" />
                            <span>{business.address}</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <Clock className="w-4 h-4 text-ink-light" />
                            <span>{hours}</span>
                        </div>
                    </div>

                    <button className="w-full md:w-auto bg-ink-dark text-paper-white px-8 py-3 rounded-full font-medium hover:bg-black transition-colors flex items-center justify-center gap-2 shadow-lg">
                        <Navigation className="w-4 h-4" />
                        Get Directions
                    </button>
                </div>
            </div>
        </main>
    );
}
