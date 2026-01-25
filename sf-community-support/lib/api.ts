/**
 * SlowCal API Client
 * 
 * Client for the SlowCal Risk Analysis backend API.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

export interface BusinessAnalysisRequest {
    business_name: string;
    address: string;
    industry?: string;
    years_in_business?: number;
}

export interface RiskDriver {
    name: string;
    trend: 'up' | 'down' | 'stable';
    contribution: number;
}

export interface StrategicAction {
    horizon: string;
    action: string;
    why: string;
    expected_outcome: string;
    impact: 'HIGH' | 'MEDIUM' | 'LOW';
    effort: 'high' | 'medium' | 'low';
}

export interface AnalysisResult {
    case_id: string;
    business_name: string;
    address: string;
    neighborhood: string;
    match_confidence: number;
    
    risk_score: number;
    risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
    risk_drivers: RiskDriver[];
    
    permit_count_6m: number;
    complaint_count_6m: number;
    incident_count_6m: number;
    
    strategy_summary: string;
    actions: StrategicAction[];
    questions: string[];
    risk_if_no_action: string;
    
    analyzed_at: string;
    pipeline_duration_ms: number;
}

export interface HealthResponse {
    status: string;
    nim_available: boolean;
    models: string[];
    timestamp: string;
}

/**
 * Check API health status
 */
export async function checkHealth(): Promise<HealthResponse> {
    const response = await fetch(`${API_BASE_URL}/health`);
    if (!response.ok) {
        throw new Error('API health check failed');
    }
    return response.json();
}

/**
 * Analyze a business for risk
 */
export async function analyzeBusinessRisk(
    request: BusinessAnalysisRequest
): Promise<AnalysisResult> {
    const response = await fetch(`${API_BASE_URL}/analyze`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
    });
    
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Analysis failed' }));
        throw new Error(error.detail || 'Analysis failed');
    }
    
    return response.json();
}

/**
 * Get risk level color class
 */
export function getRiskColor(level: string): string {
    switch (level?.toUpperCase()) {
        case 'HIGH':
            return 'text-red-500';
        case 'MEDIUM':
            return 'text-orange-500';
        case 'LOW':
            return 'text-green-500';
        default:
            return 'text-gray-500';
    }
}

/**
 * Get risk level background color class
 */
export function getRiskBgColor(level: string): string {
    switch (level?.toUpperCase()) {
        case 'HIGH':
            return 'bg-red-500';
        case 'MEDIUM':
            return 'bg-orange-500';
        case 'LOW':
            return 'bg-green-500';
        default:
            return 'bg-gray-500';
    }
}

/**
 * Format risk score as percentage
 */
export function formatRiskScore(score: number): string {
    return `${Math.round(score * 100)}%`;
}
