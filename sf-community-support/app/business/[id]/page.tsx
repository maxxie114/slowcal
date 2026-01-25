// ... imports ...
import { EvidenceList, EvidenceItem } from "@/components/business/EvidenceList";

export default async function BusinessProfilePage({ params }: { params: { id: string } }) {
    let business: Business | undefined;

    // Fetch master data
    const { data, error } = await supabase
        .from('master_model_data')
        .select('*')
        .eq('id', params.id)
        .single();

    if (data) {
        // ... (business mapping logic same as before) ...
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

    // --- Fetch Linked Evidence ---
    const { data: permits } = await supabase.from('permits').select('*').eq('business_id', params.id).order('filed_date', { ascending: false }).limit(5);
    const { data: violations } = await supabase.from('violations').select('*').eq('business_id', params.id).order('date_filed', { ascending: false }).limit(5);
    const { data: complaints } = await supabase.from('complaints_311').select('*').eq('business_id', params.id).order('opened_date', { ascending: false }).limit(5);
    const { data: incidents } = await supabase.from('sfpd_incidents').select('*').eq('business_id', params.id).order('incident_date', { ascending: false }).limit(5);

    // Map to normalized items
    const evidenceItems: EvidenceItem[] = [
        ...(permits || []).map(p => ({
            id: p.id,
            type: 'permit' as const,
            title: p.permit_type || 'Permit',
            status: p.status || 'Unknown',
            date: p.filed_date,
            description: `Type: ${p.permit_type}. Number: ${p.permit_number}`
        })),
        ...(violations || []).map(v => ({
            id: v.id,
            type: 'violation' as const,
            title: v.violation_type || 'Violation',
            status: v.status || 'Open',
            date: v.date_filed,
            description: v.description
        })),
        ...(complaints || []).map(c => ({
            id: c.id,
            type: 'complaint' as const,
            title: c.category || '311 Complaint',
            status: c.status || 'Open',
            date: c.opened_date,
            description: `Source: ${c.source}`
        })),
        ...(incidents || []).map(i => ({
            id: i.id,
            type: 'incident' as const,
            title: i.category || 'Incident',
            status: i.resolution || 'Open',
            date: i.incident_date,
            description: `Resolution: ${i.resolution}`
        }))
    ].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

    // Group by category for display
    const permitItems = evidenceItems.filter(i => i.type === 'permit');
    const negativeItems = evidenceItems.filter(i => i.type !== 'permit'); // Violations, complaints, etc.

    // ... (rest of component) ...

    return (
        <main className="min-h-screen pb-32 bg-paper-cream">
            {/* ... (Header Sections) ... */}

            <div className="max-w-4xl mx-auto px-4 md:px-8">
                {/* ... (Hero Image & Info) ... */}

                {/* ... (Story Section) ... */}

                {/* Evidence Section */}
                {(permitItems.length > 0 || negativeItems.length > 0) && (
                    <div className="max-w-2xl mx-auto mb-16">
                        <TapeStrip variant="corner-tr" className="-right-6 -top-6 w-24 opacity-60" />
                        <div className="bg-paper-white p-8 border border-stone-200 shadow-sm">
                            <h2 className="font-script text-3xl text-ink-dark mb-8 text-center">Business Activity</h2>

                            <EvidenceList title="Recent Permits" items={permitItems} />

                            {negativeItems.length > 0 && (
                                <div className="mt-8 pt-8 border-t border-stone-100">
                                    <EvidenceList title="Community Reports & Incidents" items={negativeItems} />
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* ... (Reviews Section) ... */}
            </div>

            {/* ... (Sticky Bottom Actions) ... */}
        </main>
    );
}
