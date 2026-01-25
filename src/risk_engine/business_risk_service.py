"""
Business Risk Analysis Service for Small Business Owners

This service provides an easy-to-use interface for small business owners
to assess their business risk and get actionable recommendations.

The service translates user-friendly inputs (like business name, address, 
industry type) into model features and provides clear, actionable insights.
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from enum import Enum

from .inference import RiskInference, BusinessInput, RiskPrediction


class IndustryType(Enum):
    """Common business industry types"""
    RESTAURANT = "restaurant"
    RETAIL = "retail"
    PROFESSIONAL_SERVICES = "professional_services"
    HEALTHCARE = "healthcare"
    CONSTRUCTION = "construction"
    TECHNOLOGY = "technology"
    HOSPITALITY = "hospitality"  # Hotels, B&Bs
    ENTERTAINMENT = "entertainment"
    MANUFACTURING = "manufacturing"
    OTHER = "other"


class SFNeighborhood(Enum):
    """San Francisco neighborhoods with risk data"""
    FINANCIAL_DISTRICT = "Financial District/South Beach"
    MISSION = "Mission"
    SOMA = "South of Market"
    SUNSET = "Sunset/Parkside"
    BAYVIEW = "Bayview Hunters Point"
    RICHMOND = "Outer Richmond"
    CHINATOWN = "Chinatown"
    MARINA = "Marina"
    TENDERLOIN = "Tenderloin"
    NOB_HILL = "Nob Hill"
    CASTRO = "Castro/Upper Market"
    HAYES_VALLEY = "Hayes Valley"
    NORTH_BEACH = "North Beach"
    PACIFIC_HEIGHTS = "Pacific Heights"
    POTRERO_HILL = "Potrero Hill"
    EXCELSIOR = "Excelsior"
    OTHER = "Other"


# Neighborhood statistics (from our data analysis)
NEIGHBORHOOD_STATS = {
    "Financial District/South Beach": {"permits": 4946, "avg_cost": 605416, "complaints": 2500},
    "Mission": {"permits": 2845, "avg_cost": 125000, "complaints": 3200},
    "South of Market": {"permits": 3500, "avg_cost": 450000, "complaints": 2800},
    "Sunset/Parkside": {"permits": 1200, "avg_cost": 45000, "complaints": 800},
    "Bayview Hunters Point": {"permits": 1603, "avg_cost": 126519, "complaints": 1500},
    "Outer Richmond": {"permits": 900, "avg_cost": 35000, "complaints": 600},
    "Chinatown": {"permits": 2284, "avg_cost": 279384, "complaints": 1200},
    "Marina": {"permits": 1500, "avg_cost": 85000, "complaints": 700},
    "Tenderloin": {"permits": 800, "avg_cost": 150000, "complaints": 5922},
    "Nob Hill": {"permits": 1100, "avg_cost": 120000, "complaints": 900},
    "Castro/Upper Market": {"permits": 1845, "avg_cost": 39159, "complaints": 750},
    "Hayes Valley": {"permits": 950, "avg_cost": 75000, "complaints": 650},
    "North Beach": {"permits": 1200, "avg_cost": 95000, "complaints": 850},
    "Pacific Heights": {"permits": 1800, "avg_cost": 180000, "complaints": 400},
    "Potrero Hill": {"permits": 1100, "avg_cost": 110000, "complaints": 550},
    "Excelsior": {"permits": 1016, "avg_cost": 24402, "complaints": 700},
    "Other": {"permits": 1000, "avg_cost": 50000, "complaints": 500},
}


@dataclass
class BusinessOwnerInput:
    """
    User-friendly input for small business owners.
    
    This is what the business owner provides - simple, understandable fields.
    """
    business_name: str
    year_started: int  # e.g., 2020
    industry: str  # e.g., "restaurant", "retail"
    neighborhood: str  # e.g., "Mission", "SOMA"
    has_business_license: bool = True
    is_hotel_or_bnb: bool = False  # For transient tax
    has_parking_facility: bool = False  # For parking tax


@dataclass 
class RiskAnalysisResult:
    """
    Comprehensive risk analysis result for business owners.
    
    Provides risk score, level, and actionable recommendations.
    """
    business_name: str
    risk_score: float  # 0-100 percentage
    risk_level: str  # "Low", "Medium", "High"
    confidence: float
    
    # Key insights
    top_risk_factors: List[Dict[str, str]]
    recommendations: List[str]
    neighborhood_insights: Dict[str, str]
    
    # Comparison
    industry_average_risk: float
    neighborhood_average_risk: float
    
    # Raw data for advanced users
    model_details: Dict
    
    def to_dict(self) -> Dict:
        """Convert to dictionary format"""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string for agent consumption"""
        return json.dumps(self.to_dict(), indent=indent)
    
    def to_agent_response(self) -> Dict:
        """
        Format specifically for AI agent consumption.
        Returns a structured response with clear action items.
        """
        return {
            "status": "success",
            "analysis": {
                "business_name": self.business_name,
                "risk_assessment": {
                    "score": round(self.risk_score, 1),
                    "level": self.risk_level,
                    "confidence": round(self.confidence * 100, 1)
                },
                "risk_factors": self.top_risk_factors,
                "location": self.neighborhood_insights,
                "benchmarks": {
                    "industry_average": round(self.industry_average_risk, 1),
                    "neighborhood_average": round(self.neighborhood_average_risk, 1)
                }
            },
            "recommendations": self.recommendations,
            "metadata": self.model_details
        }


class BusinessRiskService:
    """
    Main service for small business risk analysis.
    
    Usage:
    ------
    >>> from risk_engine.business_risk_service import BusinessRiskService, BusinessOwnerInput
    >>> 
    >>> service = BusinessRiskService()
    >>> 
    >>> # Business owner provides simple info
    >>> my_business = BusinessOwnerInput(
    ...     business_name="Joe's Coffee Shop",
    ...     year_started=2022,
    ...     industry="restaurant",
    ...     neighborhood="Mission"
    ... )
    >>> 
    >>> # Get comprehensive risk analysis
    >>> result = service.analyze_risk(my_business)
    >>> 
    >>> print(f"Risk Level: {result.risk_level}")
    >>> print(f"Risk Score: {result.risk_score:.1f}%")
    >>> for rec in result.recommendations:
    ...     print(f"  • {rec}")
    """
    
    # Industry risk modifiers (based on historical data)
    INDUSTRY_RISK_MODIFIERS = {
        "restaurant": 1.3,  # Higher risk
        "retail": 1.1,
        "professional_services": 0.8,  # Lower risk
        "healthcare": 0.7,
        "construction": 1.0,
        "technology": 0.9,
        "hospitality": 1.2,
        "entertainment": 1.4,  # Higher risk
        "manufacturing": 0.9,
        "other": 1.0,
    }
    
    def __init__(self, model_path: Optional[Path] = None):
        """
        Initialize the business risk service.
        
        Args:
            model_path: Optional path to the trained model
        """
        self.inference_engine = RiskInference(model_path=model_path)
        self._load_neighborhood_data()
    
    def _load_neighborhood_data(self):
        """Load neighborhood statistics for feature enrichment"""
        self.neighborhood_stats = NEIGHBORHOOD_STATS
    
    def _normalize_neighborhood(self, neighborhood: str) -> str:
        """Normalize neighborhood name to match our data"""
        neighborhood_lower = neighborhood.lower().strip()
        
        # Common aliases
        aliases = {
            "soma": "South of Market",
            "south of market": "South of Market",
            "fidi": "Financial District/South Beach",
            "financial district": "Financial District/South Beach",
            "downtown": "Financial District/South Beach",
            "mission": "Mission",
            "the mission": "Mission",
            "castro": "Castro/Upper Market",
            "upper market": "Castro/Upper Market",
            "tenderloin": "Tenderloin",
            "tl": "Tenderloin",
            "marina": "Marina",
            "chinatown": "Chinatown",
            "nob hill": "Nob Hill",
            "north beach": "North Beach",
            "pacific heights": "Pacific Heights",
            "pac heights": "Pacific Heights",
            "potrero": "Potrero Hill",
            "potrero hill": "Potrero Hill",
            "bayview": "Bayview Hunters Point",
            "hunters point": "Bayview Hunters Point",
            "sunset": "Sunset/Parkside",
            "parkside": "Sunset/Parkside",
            "richmond": "Outer Richmond",
            "outer richmond": "Outer Richmond",
            "inner richmond": "Outer Richmond",
            "excelsior": "Excelsior",
            "hayes valley": "Hayes Valley",
        }
        
        return aliases.get(neighborhood_lower, "Other")
    
    def _normalize_industry(self, industry: str) -> str:
        """Normalize industry name"""
        industry_lower = industry.lower().strip()
        
        aliases = {
            "restaurant": "restaurant",
            "food": "restaurant",
            "cafe": "restaurant",
            "coffee": "restaurant",
            "bar": "restaurant",
            "retail": "retail",
            "store": "retail",
            "shop": "retail",
            "professional": "professional_services",
            "consulting": "professional_services",
            "legal": "professional_services",
            "accounting": "professional_services",
            "healthcare": "healthcare",
            "medical": "healthcare",
            "dental": "healthcare",
            "clinic": "healthcare",
            "tech": "technology",
            "software": "technology",
            "it": "technology",
            "hotel": "hospitality",
            "hospitality": "hospitality",
            "bnb": "hospitality",
            "construction": "construction",
            "contractor": "construction",
            "entertainment": "entertainment",
            "nightclub": "entertainment",
            "manufacturing": "manufacturing",
        }
        
        return aliases.get(industry_lower, "other")
    
    def _translate_to_model_input(self, owner_input: BusinessOwnerInput) -> BusinessInput:
        """
        Translate user-friendly input to model features.
        
        This is where we enrich the simple user input with 
        neighborhood statistics and other derived features.
        """
        # Calculate business age
        current_year = datetime.now().year
        business_age = current_year - owner_input.year_started
        
        # Normalize and get neighborhood stats
        neighborhood = self._normalize_neighborhood(owner_input.neighborhood)
        stats = self.neighborhood_stats.get(neighborhood, self.neighborhood_stats["Other"])
        
        # Industry determines if they likely have NAIC code
        industry = self._normalize_industry(owner_input.industry)
        has_naic = owner_input.has_business_license  # Simplified assumption
        
        return BusinessInput(
            business_age=max(0, business_age),
            has_naic_code=has_naic,
            has_parking_tax=owner_input.has_parking_facility,
            has_transient_tax=owner_input.is_hotel_or_bnb,
            neighborhood_permits=stats["permits"],
            avg_permit_cost=stats["avg_cost"],
            neighborhood_311_cases=stats["complaints"]
        )
    
    def _generate_recommendations(
        self, 
        risk_level: str, 
        risk_score: float,
        owner_input: BusinessOwnerInput,
        prediction: RiskPrediction
    ) -> List[str]:
        """Generate actionable recommendations based on risk analysis"""
        recommendations = []
        
        industry = self._normalize_industry(owner_input.industry)
        business_age = datetime.now().year - owner_input.year_started
        
        # Risk level specific recommendations
        if risk_level == "High":
            recommendations.append(
                "⚠️ Consider consulting with a business advisor to review your operations"
            )
            recommendations.append(
                "📊 Review your cash flow and ensure 6+ months of operating reserves"
            )
        elif risk_level == "Medium":
            recommendations.append(
                "📈 Focus on building consistent revenue streams"
            )
        
        # Age-based recommendations
        if business_age < 2:
            recommendations.append(
                "🆕 New businesses should prioritize customer acquisition and retention"
            )
            recommendations.append(
                "💰 Consider SBA loans or grants for new businesses in SF"
            )
        elif business_age < 5:
            recommendations.append(
                "📋 Ensure all permits and licenses are up to date"
            )
        
        # Industry-specific recommendations
        if industry == "restaurant":
            recommendations.append(
                "🍽️ Restaurant tip: Monitor food costs and labor closely - aim for <30% each"
            )
            recommendations.append(
                "📱 Consider delivery partnerships to expand revenue"
            )
        elif industry == "retail":
            recommendations.append(
                "🛍️ Retail tip: Build an online presence to complement your storefront"
            )
        elif industry == "professional_services":
            recommendations.append(
                "💼 Professional services have lower risk - focus on client retention"
            )
        
        # Neighborhood-specific
        neighborhood = self._normalize_neighborhood(owner_input.neighborhood)
        if neighborhood == "Tenderloin":
            recommendations.append(
                "🏘️ Consider joining local business associations for community support"
            )
        elif neighborhood in ["Financial District/South Beach", "South of Market"]:
            recommendations.append(
                "🏢 High-rent area: Ensure margins support your lease costs"
            )
        
        # License recommendation
        if not owner_input.has_business_license:
            recommendations.append(
                "📜 IMPORTANT: Obtain proper business registration and licenses"
            )
        
        return recommendations[:5]  # Return top 5 recommendations
    
    def _get_neighborhood_insights(self, neighborhood: str) -> Dict[str, str]:
        """Get insights about the business neighborhood"""
        normalized = self._normalize_neighborhood(neighborhood)
        stats = self.neighborhood_stats.get(normalized, self.neighborhood_stats["Other"])
        
        # Determine neighborhood risk level based on complaints
        if stats["complaints"] > 3000:
            complaint_level = "High activity area"
        elif stats["complaints"] > 1000:
            complaint_level = "Moderate activity area"
        else:
            complaint_level = "Lower activity area"
        
        # Permit activity
        if stats["permits"] > 2000:
            permit_level = "High development activity"
        elif stats["permits"] > 1000:
            permit_level = "Moderate development"
        else:
            permit_level = "Stable neighborhood"
        
        return {
            "neighborhood": normalized,
            "development_activity": permit_level,
            "avg_permit_cost": f"${stats['avg_cost']:,.0f}",
            "community_activity": complaint_level,
            "business_environment": self._assess_business_environment(stats)
        }
    
    def _assess_business_environment(self, stats: Dict) -> str:
        """Assess overall business environment quality"""
        score = 0
        
        # More permits = more business activity (good)
        if stats["permits"] > 1500:
            score += 1
        
        # Very high complaints = challenging environment
        if stats["complaints"] > 3000:
            score -= 1
        elif stats["complaints"] < 1000:
            score += 1
        
        # High permit costs = established area
        if stats["avg_cost"] > 100000:
            score += 1
        
        if score >= 2:
            return "Favorable for business"
        elif score >= 0:
            return "Moderate business environment"
        else:
            return "Challenging environment - extra planning recommended"
    
    def analyze_risk(self, owner_input: BusinessOwnerInput) -> RiskAnalysisResult:
        """
        Perform comprehensive risk analysis for a business.
        
        Args:
            owner_input: Business owner's input with simple, understandable fields
        
        Returns:
            RiskAnalysisResult with risk score, recommendations, and insights
        """
        # Translate to model input
        model_input = self._translate_to_model_input(owner_input)
        
        # Get model prediction
        prediction = self.inference_engine.predict(model_input)
        
        # Apply industry modifier
        industry = self._normalize_industry(owner_input.industry)
        industry_modifier = self.INDUSTRY_RISK_MODIFIERS.get(industry, 1.0)
        adjusted_score = min(1.0, prediction.risk_score * industry_modifier)
        
        # Determine adjusted risk level
        if adjusted_score < 0.4:
            risk_level = "Low"
        elif adjusted_score < 0.7:
            risk_level = "Medium"
        else:
            risk_level = "High"
        
        # Get top risk factors in user-friendly format
        top_factors = []
        for feature, importance in sorted(
            prediction.feature_contributions.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]:
            factor_name = self._humanize_feature_name(feature)
            top_factors.append({
                "factor": factor_name,
                "impact": f"{importance:.0%}",
                "description": self._get_factor_description(feature, model_input)
            })
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            risk_level, adjusted_score, owner_input, prediction
        )
        
        # Get neighborhood insights
        neighborhood_insights = self._get_neighborhood_insights(owner_input.neighborhood)
        
        # Industry and neighborhood averages (simplified)
        industry_avg = 0.5 * industry_modifier
        neighborhood = self._normalize_neighborhood(owner_input.neighborhood)
        stats = self.neighborhood_stats.get(neighborhood, self.neighborhood_stats["Other"])
        neighborhood_avg = 0.4 + (stats["complaints"] / 10000)  # Simple heuristic
        
        return RiskAnalysisResult(
            business_name=owner_input.business_name,
            risk_score=adjusted_score * 100,  # Convert to percentage
            risk_level=risk_level,
            confidence=prediction.confidence,
            top_risk_factors=top_factors,
            recommendations=recommendations,
            neighborhood_insights=neighborhood_insights,
            industry_average_risk=industry_avg * 100,
            neighborhood_average_risk=min(100, neighborhood_avg * 100),
            model_details={
                "raw_risk_score": prediction.risk_score,
                "industry_modifier": industry_modifier,
                "model_roc_auc": self.inference_engine.roc_auc
            }
        )
    
    def _humanize_feature_name(self, feature: str) -> str:
        """Convert technical feature name to user-friendly text"""
        mapping = {
            "business_age": "Business Age",
            "has_naic_code": "Business Registration",
            "has_parking_tax": "Parking Facility",
            "has_transient_tax": "Hospitality Business",
            "neighborhood_permits": "Neighborhood Development",
            "avg_permit_cost": "Area Investment Level",
            "neighborhood_311_cases": "Neighborhood Activity"
        }
        return mapping.get(feature, feature.replace("_", " ").title())
    
    def _get_factor_description(self, feature: str, model_input: BusinessInput) -> str:
        """Get description of how a factor affects risk"""
        descriptions = {
            "business_age": f"Your business is {model_input.business_age} years old",
            "has_naic_code": "Proper registration reduces risk" if model_input.has_naic_code else "Missing registration increases risk",
            "neighborhood_permits": f"{model_input.neighborhood_permits} permits in your area",
            "avg_permit_cost": f"Average area investment: ${model_input.avg_permit_cost:,.0f}",
            "neighborhood_311_cases": f"{model_input.neighborhood_311_cases} service requests in area"
        }
        return descriptions.get(feature, "")
    
    def quick_risk_check(
        self,
        business_name: str,
        year_started: int,
        industry: str,
        neighborhood: str
    ) -> Dict:
        """
        Quick risk check with minimal inputs.
        
        Returns a simple dictionary with key risk info.
        
        Example:
            >>> service.quick_risk_check(
            ...     business_name="My Shop",
            ...     year_started=2023,
            ...     industry="retail",
            ...     neighborhood="Mission"
            ... )
        """
        owner_input = BusinessOwnerInput(
            business_name=business_name,
            year_started=year_started,
            industry=industry,
            neighborhood=neighborhood
        )
        
        result = self.analyze_risk(owner_input)
        
        return {
            "business": business_name,
            "risk_score": f"{result.risk_score:.1f}%",
            "risk_level": result.risk_level,
            "top_recommendation": result.recommendations[0] if result.recommendations else None,
            "neighborhood": result.neighborhood_insights["neighborhood"]
        }
    
    def analyze_risk_json(self, owner_input: BusinessOwnerInput) -> str:
        """
        Perform risk analysis and return JSON string.
        
        This method is designed for agent-to-agent communication.
        
        Args:
            owner_input: Business owner's input
        
        Returns:
            JSON string with complete risk analysis
        """
        result = self.analyze_risk(owner_input)
        return result.to_json()
    
    def analyze_risk_for_agent(self, owner_input: BusinessOwnerInput) -> Dict:
        """
        Perform risk analysis and return structured dict for AI agents.
        
        This method returns a well-structured response that AI agents
        can easily parse and act upon.
        
        Args:
            owner_input: Business owner's input
        
        Returns:
            Dictionary with structured analysis for agent consumption
        """
        result = self.analyze_risk(owner_input)
        return result.to_agent_response()
    
    def analyze_from_json(self, json_input: str) -> str:
        """
        Accept JSON input and return JSON output.
        
        Perfect for agent-to-agent communication via JSON.
        
        Args:
            json_input: JSON string with business details
                Expected format:
                {
                    "business_name": "My Business",
                    "year_started": 2020,
                    "industry": "restaurant",
                    "neighborhood": "Mission",
                    "has_business_license": true,
                    "is_hotel_or_bnb": false,
                    "has_parking_facility": false
                }
        
        Returns:
            JSON string with complete risk analysis
        """
        try:
            data = json.loads(json_input)
            
            owner_input = BusinessOwnerInput(
                business_name=data.get("business_name", "Unknown Business"),
                year_started=data.get("year_started", datetime.now().year),
                industry=data.get("industry", "other"),
                neighborhood=data.get("neighborhood", "Other"),
                has_business_license=data.get("has_business_license", True),
                is_hotel_or_bnb=data.get("is_hotel_or_bnb", False),
                has_parking_facility=data.get("has_parking_facility", False)
            )
            
            result = self.analyze_risk(owner_input)
            return json.dumps(result.to_agent_response(), indent=2)
            
        except json.JSONDecodeError as e:
            return json.dumps({
                "status": "error",
                "error_type": "invalid_json",
                "message": f"Failed to parse input JSON: {str(e)}"
            }, indent=2)
        except Exception as e:
            return json.dumps({
                "status": "error", 
                "error_type": "analysis_failed",
                "message": f"Risk analysis failed: {str(e)}"
            }, indent=2)


# Convenience function for quick access
def analyze_my_business(
    business_name: str,
    year_started: int,
    industry: str,
    neighborhood: str,
    has_license: bool = True,
    is_hotel: bool = False,
    has_parking: bool = False
) -> RiskAnalysisResult:
    """
    Quick function to analyze business risk.
    
    Example:
        >>> from risk_engine.business_risk_service import analyze_my_business
        >>> 
        >>> result = analyze_my_business(
        ...     business_name="Joe's Coffee",
        ...     year_started=2022,
        ...     industry="restaurant",
        ...     neighborhood="Mission"
        ... )
        >>> 
        >>> print(f"Risk: {result.risk_level} ({result.risk_score:.1f}%)")
        >>> for rec in result.recommendations:
        ...     print(f"  • {rec}")
    """
    service = BusinessRiskService()
    
    owner_input = BusinessOwnerInput(
        business_name=business_name,
        year_started=year_started,
        industry=industry,
        neighborhood=neighborhood,
        has_business_license=has_license,
        is_hotel_or_bnb=is_hotel,
        has_parking_facility=has_parking
    )
    
    return service.analyze_risk(owner_input)


def analyze_business_json(json_input: str) -> str:
    """
    Analyze business risk from JSON input, return JSON output.
    
    This is the main entry point for agent-to-agent communication.
    
    Args:
        json_input: JSON string with business details
            {
                "business_name": "My Business",
                "year_started": 2020,
                "industry": "restaurant",
                "neighborhood": "Mission"
            }
    
    Returns:
        JSON string with structured risk analysis
    
    Example:
        >>> from risk_engine.business_risk_service import analyze_business_json
        >>> 
        >>> input_json = '''
        ... {
        ...     "business_name": "Joe's Cafe",
        ...     "year_started": 2023,
        ...     "industry": "cafe",
        ...     "neighborhood": "Mission"
        ... }
        ... '''
        >>> 
        >>> result_json = analyze_business_json(input_json)
        >>> print(result_json)
    """
    service = BusinessRiskService()
    return service.analyze_from_json(json_input)


def get_risk_analysis_schema() -> Dict:
    """
    Return the JSON schema for input/output.
    
    Useful for agents to understand the expected format.
    """
    return {
        "input_schema": {
            "type": "object",
            "required": ["business_name", "year_started", "industry", "neighborhood"],
            "properties": {
                "business_name": {
                    "type": "string",
                    "description": "Name of the business"
                },
                "year_started": {
                    "type": "integer",
                    "description": "Year the business was started (e.g., 2020)"
                },
                "industry": {
                    "type": "string",
                    "description": "Business industry type",
                    "enum": ["restaurant", "retail", "professional_services", "healthcare", 
                             "construction", "technology", "hospitality", "entertainment", 
                             "manufacturing", "other"]
                },
                "neighborhood": {
                    "type": "string",
                    "description": "San Francisco neighborhood name"
                },
                "has_business_license": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether the business has proper licensing"
                },
                "is_hotel_or_bnb": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether this is a hotel or B&B business"
                },
                "has_parking_facility": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether the business has a parking facility"
                }
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["success", "error"]},
                "analysis": {
                    "type": "object",
                    "properties": {
                        "business_name": {"type": "string"},
                        "risk_assessment": {
                            "type": "object",
                            "properties": {
                                "score": {"type": "number", "minimum": 0, "maximum": 100},
                                "level": {"type": "string", "enum": ["Low", "Medium", "High"]},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 100}
                            }
                        },
                        "risk_factors": {"type": "array"},
                        "location": {"type": "object"},
                        "benchmarks": {"type": "object"}
                    }
                },
                "recommendations": {"type": "array", "items": {"type": "string"}},
                "metadata": {"type": "object"}
            }
        }
    }


if __name__ == "__main__":
    # Demo usage
    print("=" * 60)
    print("SMALL BUSINESS RISK ANALYZER")
    print("=" * 60)
    
    # Example: New coffee shop in the Mission
    result = analyze_my_business(
        business_name="Sunrise Coffee",
        year_started=2023,
        industry="cafe",
        neighborhood="Mission"
    )
    
    print(f"\n📊 Analysis for: {result.business_name}")
    print(f"   Risk Score: {result.risk_score:.1f}%")
    print(f"   Risk Level: {result.risk_level}")
    print(f"   Confidence: {result.confidence:.0%}")
    
    print(f"\n🔍 Top Risk Factors:")
    for factor in result.top_risk_factors:
        print(f"   • {factor['factor']}: {factor['impact']}")
        if factor['description']:
            print(f"     {factor['description']}")
    
    print(f"\n📍 Neighborhood: {result.neighborhood_insights['neighborhood']}")
    print(f"   Environment: {result.neighborhood_insights['business_environment']}")
    
    print(f"\n💡 Recommendations:")
    for rec in result.recommendations:
        print(f"   {rec}")
    
    print("\n" + "=" * 60)
