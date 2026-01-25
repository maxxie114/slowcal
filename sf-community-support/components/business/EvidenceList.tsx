
import { EvidenceCard, EvidenceItem } from "./EvidenceCard";

export function EvidenceList({ title, items }: { title: string, items: EvidenceItem[] }) {
    if (!items || items.length === 0) return null;

    return (
        <div className="mb-8">
            <h3 className="font-script text-2xl text-ink-medium mb-4">{title}</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {items.map((item) => (
                    <EvidenceCard key={`${item.type}-${item.id}`} item={item} />
                ))}
            </div>
        </div>
    );
}
