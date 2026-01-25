/**
 * Type definitions for SlowCal
 */

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';
export type Category = 'cafe' | 'restaurant' | 'retail' | 'service' | 'bar' | 'other';

export interface Business {
    id: string;
    name: string;
    category: Category;
    neighborhood: string;
    address: string;
    lat: number;
    lng: number;
    photoUrl?: string;
    riskScore: number;
    riskLevel: RiskLevel;
    tagline?: string;
    story?: string;
    businessAge?: number;
}

export interface RiskFactor {
    name: string;
    value: number;
    color: string;
    label: string;
}

export interface SurvivalPlanSection {
    id: string;
    title: string;
    status: 'critical' | 'moderate' | 'completed';
    onePager: {
        title: string;
        problem: string;
        context: string;
        actionPlan: { step: number; text: string }[];
        resources: string[];
    };
}
