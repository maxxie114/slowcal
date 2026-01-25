import { ArrowLeft, MapPin, Clock, Navigation, Star } from "lucide-react";
import Link from "next/link";
import { PolaroidImage } from "@/components/ui/PolaroidImage";
import { RiskIndicator } from "@/components/ui/RiskIndicator";
import { TapeStrip } from "@/components/ui/TapeStrip";
import { cn } from "@/lib/utils";
import { notFound } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { Business } from "@/lib/types";

export default async function BusinessProfilePage({ params }: { params: { id: string } }) {
    let business: Business | undefined;

    // Fetch directly from Supabase
    const { data, error } = await supabase
        .from('master_model_data')
        .select('*')
        .eq('id', params.id)
        .single();
    
    if (data) {
            business = {
            id: data.id.toString(),
            name: data.dba_name || data.ownership_name || "Unknown Business",
            category: 'other',
            neighborhood: data.neighborhood || "Unknown Neighborhood",
            address: data.full_business_address || "",
            lat: data.latitude ? parseFloat(data.latitude) : 37.7749,
            lng: data.longitude ? parseFloat(data.longitude) : -122.4194,
            photoUrl: "https://images.unsplash.com/photo-1519167758481-83f550bb49b3?auto=format&fit=crop&q=80&w=800",
            riskScore: Math.round((data.risk_score || 0) * 100),
            riskLevel: data.risk_level?.toLowerCase() === 'high' ? 'high' : 'critical',
            tagline: data.naic_code_description || "Local Business",
            story: "", 
            businessAge: data.business_age
        };
    }

    if (!business) {
        return notFound();
    }

    // Default data for fields not in the main data source yet
    const tags = [business.category, business.neighborhood];
    if (business.tagline) tags.push(business.tagline.slice(0, 20) + (business.tagline.length > 20 ? '...' : ''));

    const riskReason = business.riskLevel === 'critical' 
        ? "Facing immediate displacement pressure due to significant rent increases."
        : business.riskLevel === 'high'
        ? "Lease renewal coming up with expected rate hikes."
        : business.riskLevel === 'moderate'
        ? "Steady business but operating on thin margins."
        : "Currently stable but needs community support to thrive.";
    
    // We don't have real hours yet, so we shouldn't show fake ones.
    const hours = null; 

    const destinationQuery = business.address && business.address.trim().length > 0
        ? encodeURIComponent(business.address)
        : `${business.lat},${business.lng}`;
    const googleMapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${destinationQuery}`;
    const appleMapsUrl = `https://maps.apple.com/?daddr=${destinationQuery}`;
    
    // Use the tagline as the intro to the story if story is missing
    const story = business.story || "";

    // No fake reviews
    const reviews: any[] = [];

    // Only show gallery if we have actual unique images, otherwise just show the main one nicely
    // Since we only have a placeholder photoUrl currently, we should just show that one main image
    // instead of pretending we have a gallery of 3 identical images.
    const displayImages = [{ src: business.photoUrl, alt: business.name, caption: "Storefront" }];

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
                {/* Single Hero Image (since we don't have a gallery) */}
                <div className="relative py-8 md:py-12 mb-8 flex justify-center">
                    <div className="w-full max-w-md transform rotate-1 transition-transform hover:rotate-0 hover:scale-[1.02] duration-500">
                        <PolaroidImage
                            src={displayImages[0].src}
                            alt={displayImages[0].alt}
                            caption={displayImages[0].caption}
                            rotation="none"
                            className="w-full aspect-[4/3] object-cover"
                            fill
                        />
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

                {/* Story Section - Only show if we have content or at least a description */}
                {(story || business.tagline) && (
                <div className="relative max-w-2xl mx-auto mb-16">
                    <TapeStrip variant="corner-tl" className="-left-4 -top-4 w-32 opacity-80" />
                    <TapeStrip variant="corner-br" className="-right-4 -bottom-4 w-32 opacity-80" />

                    <div className="bg-paper-white p-8 md:p-12 shadow-paper rotate-[0.5deg]">
                        <h2 className="font-script text-3xl text-ink-medium mb-6">About Us</h2>
                        <div className="prose prose-stone prose-lg font-serif leading-relaxed text-ink-medium">
                            {story ? (
                                story.split('\n').map((paragraph, i) => (
                                    paragraph.trim() && <p key={i} className="mb-4">{paragraph}</p>
                                ))
                            ) : (
                                <p className="mb-4">{business.tagline}</p>
                            )}
                            {business.businessAge && (
                                <p className="text-sm text-stone-500 mt-6 border-t pt-4 border-stone-100">
                                    Serving the community for {business.businessAge} years.
                                </p>
                            )}
                        </div>
                    </div>
                </div>
                )}

                {/* Reviews Section - Hidden if no reviews */}
                {reviews.length > 0 && (
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
                )}
            </div>

            {/* Sticky Bottom Actions */}
            <div className="fixed bottom-0 left-0 right-0 bg-white/95 backdrop-blur-md border-t border-stone-200 p-4 shadow-lg-up z-50">
                <div className="max-w-4xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
                    <div className="flex flex-col md:flex-row gap-4 md:gap-8 text-sm text-ink-medium">
                        <div className="flex items-center gap-2">
                            <MapPin className="w-4 h-4 text-risk-medium" />
                            <span>{business.address}</span>
                        </div>
                        {hours && (
                            <div className="flex items-center gap-2">
                                <Clock className="w-4 h-4 text-ink-light" />
                                <span>{hours}</span>
                            </div>
                        )}
                    </div>

                    <div className="flex w-full md:w-auto items-center gap-3">
                        <a
                            href={googleMapsUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="w-full md:w-auto bg-ink-dark text-paper-white px-8 py-3 rounded-full font-medium hover:bg-black transition-colors flex items-center justify-center gap-2 shadow-lg"
                        >
                            <Navigation className="w-4 h-4" />
                            Get Directions
                        </a>
                        <a
                            href={appleMapsUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-ink-medium underline underline-offset-4 hover:text-ink-dark"
                        >
                            Apple Maps
                        </a>
                    </div>
                </div>
            </div>
        </main>
    );
}
