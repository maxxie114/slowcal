"""
FastAPI Server for SlowCal Risk Analysis API

Provides REST endpoints for the Next.js frontend to:
- Analyze business risk
- Get strategy recommendations
- Health checks
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

# Import SlowCal modules
from agents.case_manager import CaseManagerAgent
from tools.nim_client import NIMClient
from utils.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SlowCal Risk Analysis API",
    description="SF Small Business Risk Intelligence Platform API",
    version="1.0.0"
)

# CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize case manager
case_manager = CaseManagerAgent()


# ============================================
# Request/Response Models
# ============================================

class BusinessAnalysisRequest(BaseModel):
    """Request to analyze a business"""
    business_name: str
    address: str
    industry: Optional[str] = None
    years_in_business: Optional[int] = None


class RiskDriver(BaseModel):
    """A risk driver with trend"""
    name: str
    trend: str  # up, down, stable
    contribution: float


def format_driver_name(raw_name: str) -> str:
    """Convert feature names to human-readable format"""
    name_map = {
        "business_age_years": "Business Age",
        "permit_count_6m": "Recent Permits",
        "permit_count_3m": "Permits (3 months)",
        "permit_count_12m": "Permits (12 months)",
        "complaint_count_6m": "311 Complaints",
        "complaint_count_3m": "Complaints (3 months)",
        "complaint_count_12m": "Complaints (12 months)",
        "incident_count_6m": "Crime Incidents",
        "dbi_count_6m": "Building Violations",
        "eviction_rate_relative": "Eviction Risk",
        "vacancy_rate": "Vacancy Rate",
        "has_open_violations": "Open Violations",
        "neighborhood_stress_level": "Neighborhood Stress",
        "permit_trend": "Permit Trend",
        "complaint_trend": "Complaint Trend",
        "incident_trend": "Incident Trend",
        "is_active": "Business Status",
        "has_naic_code": "Industry Classification",
        "avg_permit_cost_12m": "Permit Costs",
        "business_relevant_complaints_6m": "Business-Related Complaints",
        "business_relevant_incidents_6m": "Business-Related Incidents",
        "open_closed_ratio": "Open/Closed Ratio",
    }
    return name_map.get(raw_name, raw_name.replace("_", " ").title())


class StrategicAction(BaseModel):
    """A recommended action"""
    horizon: str  # "2 weeks", "1-2 months", etc.
    action: str
    why: str
    expected_outcome: str
    impact: str  # HIGH, MEDIUM, LOW
    effort: str  # high, medium, low


class AnalysisResult(BaseModel):
    """Full analysis result"""
    case_id: str
    business_name: str
    address: str
    neighborhood: str
    match_confidence: float
    
    # Risk assessment
    risk_score: float
    risk_level: str  # LOW, MEDIUM, HIGH
    risk_drivers: List[RiskDriver]
    
    # Data signals
    permit_count_6m: int
    complaint_count_6m: int
    incident_count_6m: int
    
    # Strategy
    strategy_summary: str
    actions: List[StrategicAction]
    questions: List[str]
    risk_if_no_action: str
    
    # Metadata
    analyzed_at: str
    pipeline_duration_ms: int


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    nim_available: bool
    models: List[str]
    timestamp: str


# ============================================
# API Endpoints
# ============================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API and NIM service health"""
    nim_client = NIMClient()
    nim_ready = nim_client.is_ready()
    models = nim_client.get_models() if nim_ready else []
    
    return HealthResponse(
        status="healthy" if nim_ready else "degraded",
        nim_available=nim_ready,
        models=models,
        timestamp=datetime.utcnow().isoformat()
    )


@app.post("/analyze", response_model=AnalysisResult)
async def analyze_business(request: BusinessAnalysisRequest):
    """
    Run full risk analysis on a business.
    
    This is the main endpoint that:
    1. Queries SF Open Data for business info
    2. Aggregates signals from multiple data sources
    3. Runs ML risk prediction
    4. Generates strategic recommendations via LLM
    """
    try:
        # Combine name and address for search
        query = f"{request.business_name}, {request.address}"
        
        logger.info(f"Starting analysis for: {query}")
        
        # Run the full pipeline using analyze method
        result = case_manager.analyze(
            business_query=query,
            horizon_months=6
        )
        
        # PipelineResult is a dataclass with: success, response, context, duration_ms
        if not result.success:
            raise HTTPException(status_code=500, detail="Analysis pipeline failed")
        
        # Extract data from the response dict
        response = result.response
        entity = response.get("entity", {})
        risk = response.get("risk", {})
        strategy = response.get("strategy", {})
        signals = response.get("signals", {})
        
        # Debug: log signals structure
        logger.info(f"Signals keys: {list(signals.keys())}")
        if "permits" in signals:
            raw_permits = signals['permits']
            logger.info(f"Raw permits data keys: {list(raw_permits.keys()) if isinstance(raw_permits, dict) else 'not a dict'}")
        if "complaints_311" in signals:
            raw_complaints = signals['complaints_311']
            logger.info(f"Raw complaints data keys: {list(raw_complaints.keys()) if isinstance(raw_complaints, dict) else 'not a dict'}")
        if "sfpd_incidents" in signals:
            raw_incidents = signals['sfpd_incidents']
            logger.info(f"Raw incidents data keys: {list(raw_incidents.keys()) if isinstance(raw_incidents, dict) else 'not a dict'}")
        
        # Parse risk drivers
        risk_drivers = []
        logger.info(f"Raw top_drivers: {risk.get('top_drivers', [])[:2]}")  # Log first 2
        for driver in risk.get("top_drivers", [])[:5]:
            if isinstance(driver, dict):
                # Try multiple possible key names: driver, feature, name
                raw_name = driver.get("driver") or driver.get("feature") or driver.get("name", "unknown")
                risk_drivers.append(RiskDriver(
                    name=format_driver_name(raw_name),
                    trend=driver.get("direction", driver.get("trend", "stable")),
                    contribution=driver.get("contribution", 0.0)
                ))
            elif isinstance(driver, (list, tuple)) and len(driver) >= 2:
                risk_drivers.append(RiskDriver(
                    name=format_driver_name(str(driver[0])),
                    trend="stable",
                    contribution=float(driver[1]) if len(driver) > 1 else 0.0
                ))
        
        # Parse actions
        actions = []
        for action in strategy.get("actions", [])[:8]:
            if isinstance(action, dict):
                actions.append(StrategicAction(
                    horizon=action.get("horizon", "1-2 months"),
                    action=action.get("action", ""),
                    why=action.get("why", ""),
                    expected_outcome=action.get("expected_outcome", ""),
                    impact=action.get("impact", "MEDIUM"),
                    effort=action.get("effort", "medium")
                ))
        
        # Extract signal counts - handle both direct signals and nested 'signals' key
        def get_signal(source_dict):
            """Extract signals from source, handling nested 'signals' key"""
            if not source_dict:
                return {}
            if isinstance(source_dict, dict) and 'signals' in source_dict:
                return source_dict.get('signals', {})
            return source_dict
        
        permits = get_signal(signals.get("permits", {}))
        complaints = get_signal(signals.get("complaints_311", {}))
        incidents = get_signal(signals.get("sfpd_incidents", {}))
        
        permit_count = permits.get("permit_count_6m", 0) or 0
        complaint_count = complaints.get("complaint_count_6m", 0) or 0
        incident_count = incidents.get("incident_count_6m", 0) or 0
        
        logger.info(f"Extracted counts - permits: {permit_count}, complaints: {complaint_count}, incidents: {incident_count}")
        
        return AnalysisResult(
            case_id=result.context.case_id,
            business_name=entity.get("business_name", request.business_name),
            address=entity.get("address", request.address),
            neighborhood=entity.get("neighborhood", "Unknown"),
            match_confidence=entity.get("confidence", 0.0),
            
            risk_score=risk.get("score", 0.5),
            risk_level=risk.get("band", "MEDIUM").upper(),
            risk_drivers=risk_drivers,
            
            permit_count_6m=int(permit_count),
            complaint_count_6m=int(complaint_count),
            incident_count_6m=int(incident_count),
            
            strategy_summary=strategy.get("summary", "Analysis complete."),
            actions=actions,
            questions=strategy.get("questions_for_user", [])[:5],
            risk_if_no_action=strategy.get("risk_if_no_action", ""),
            
            analyzed_at=datetime.utcnow().isoformat(),
            pipeline_duration_ms=int(result.duration_ms)
        )
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/business/{business_id}")
async def get_business(business_id: str):
    """Get cached business analysis by ID (from Supabase)"""
    # This would query Supabase for stored results
    # For now, return a placeholder
    raise HTTPException(status_code=404, detail="Business not found")


# ============================================
# Run Server
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8080,
        reload=True
    )
