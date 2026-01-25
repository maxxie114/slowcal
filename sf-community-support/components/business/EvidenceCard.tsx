
import { AlertCircle, FileText, Activity } from "lucide-react";
import { format } from "date-fns";

export type EvidenceType = 'permit' | 'violation' | 'complaint' | 'incident';

export interface EvidenceItem {
    id: string | number;
    type: EvidenceType;
    title: string;
    status: string;
    date: string;
    description?: string;
    severity?: 'low' | 'medium' | 'high';
}

export function EvidenceCard({ item }: { item: EvidenceItem }) {
    const statusColors: Record<string, string> = {
        'issued': 'bg-green-100 text-green-700',
        'approved': 'bg-green-100 text-green-700',
        'completed': 'bg-blue-100 text-blue-700',
        'filed': 'bg-yellow-100 text-yellow-700',
        'expired': 'bg-stone-100 text-stone-500',
        'open': 'bg-red-100 text-red-700',
        'resolved': 'bg-green-100 text-green-700',
        'closed': 'bg-stone-100 text-stone-600',
        'cited': 'bg-red-100 text-red-700',
    };

    const StatusIcon = item.type === 'violation' || item.type === 'incident' ? AlertCircle : item.type === 'permit' ? FileText : Activity;

    return (
        <div className="bg-white border border-stone-100 p-4 rounded-lg shadow-sm hover:shadow-md transition-shadow">
            <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-2">
                    <StatusIcon className="w-4 h-4 text-stone-400" />
                    <span className="font-semibold text-sm text-ink-dark">{item.title}</span>
                </div>
                <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${statusColors[item.status.toLowerCase()] || 'bg-stone-100 text-stone-500'}`}>
                    {item.status}
                </span>
            </div>
            {item.description && (
                <p className="text-xs text-stone-500 mb-2 line-clamp-2">{item.description}</p>
            )}
            <div className="text-[10px] text-stone-400 flex items-center justify-between mt-2">
                <span>{item.type.toUpperCase()}</span>
                <span>{item.date ? format(new Date(item.date), 'MMM d, yyyy') : 'N/A'}</span>
            </div>
        </div>
    );
}
