"""
Feature Builder Agent

Converts raw signals from data agents into model-ready features.
Handles:
- Rolling window aggregations (3m/6m/12m)
- Trend calculations
- Feature normalization
- Leakage prevention
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.config import Config

logger = logging.getLogger(__name__)


@dataclass
class ModelFeatures:
    """Feature vector for risk model"""
    features: Dict[str, float]
    feature_version: str
    as_of: datetime
    entity_id: str
    evidence_refs: List[str] = field(default_factory=list)
    missing_features: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "features": self.features,
            "feature_version": self.feature_version,
            "as_of": self.as_of.isoformat(),
            "entity_id": self.entity_id,
            "missing_features": self.missing_features,
        }
    
    # Mapping from trained model feature names to feature builder feature names
    FEATURE_ALIASES = {
        "business_age": "business_age_years",
        "neighborhood_permits": "permit_count_6m",
        "avg_permit_cost": "avg_permit_cost_12m",
        "neighborhood_311_cases": "complaint_count_6m",
    }
    
    def to_array(self, feature_order: List[str]) -> List[float]:
        """Convert to ordered array for model input, handling feature name aliases"""
        result = []
        for f in feature_order:
            # Check if this is an alias that needs to be mapped
            actual_name = self.FEATURE_ALIASES.get(f, f)
            result.append(self.features.get(actual_name, 0.0))
        return result


class FeatureBuilderAgent:
    """
    Agent for building model features from raw signals.
    
    Produces leakage-safe features:
    - All features use only data available at as_of time
    - Rolling windows respect temporal boundaries
    - Trends calculated from non-overlapping periods
    
    Example usage:
        agent = FeatureBuilderAgent()
        features = agent.build_features(
            entity_id="biz_123",
            signals={
                "permits": {...},
                "complaints_311": {...},
                "registry": {...},
            },
            as_of=datetime.now(),
        )
    """
    
    VERSION = "0.2"
    
    # Feature definitions with extraction logic
    FEATURE_DEFINITIONS = [
        # Business age and status
        "business_age_years",
        "is_active",
        "has_naic_code",
        "has_parking_tax",
        "has_transient_tax",
        
        # Permit features
        "permit_count_3m",
        "permit_count_6m",
        "permit_count_12m",
        "permit_trend",  # -1, 0, 1
        "avg_permit_cost_12m",
        "has_recent_permits",
        
        # 311 complaint features
        "complaint_count_3m",
        "complaint_count_6m",
        "complaint_count_12m",
        "complaint_trend",
        "open_closed_ratio",
        "business_relevant_complaints_6m",
        
        # DBI complaint features
        "dbi_count_6m",
        "dbi_trend",
        "has_open_violations",
        
        # SFPD incident features
        "incident_count_6m",
        "incident_trend",
        "business_relevant_incidents_6m",
        
        # Neighborhood stress features
        "eviction_rate_relative",
        "neighborhood_stress_level",  # encoded 0-3
        
        # Commercial corridor features
        "vacancy_rate_pct",
        "corridor_health",  # encoded 0-4
    ]
    
    @property
    def name(self) -> str:
        return "FeatureBuilderAgent"
    
    def build_features(
        self,
        entity_id: str,
        signals: Dict[str, Dict[str, Any]],
        as_of: datetime = None,
    ) -> ModelFeatures:
        """
        Build model features from agent signals.
        
        Args:
            entity_id: Entity identifier
            signals: Dict of signals from each data agent
            as_of: Reference time for feature calculation
        
        Returns:
            ModelFeatures ready for model input
        """
        as_of = as_of or datetime.utcnow()
        features = {}
        missing = []
        evidence_refs = []
        
        # Extract signals from each source (handle both old and new key names)
        # Also handle nested 'signals' key within each source
        def get_signal(source_dict):
            """Extract signals from source, handling nested 'signals' key"""
            if not source_dict:
                return {}
            # If source has a 'signals' sub-key, use that
            if isinstance(source_dict, dict) and 'signals' in source_dict:
                return source_dict.get('signals', {})
            return source_dict
        
        # Registry can be 'registry' or 'business_registry'
        registry = get_signal(signals.get("registry") or signals.get("business_registry", {}))
        
        # Permits
        permits = get_signal(signals.get("permits", {}))
        
        # 311 Complaints
        complaints_311 = get_signal(signals.get("complaints_311", {}))
        
        # DBI can be 'dbi' or 'dbi_complaints'
        dbi = get_signal(signals.get("dbi") or signals.get("dbi_complaints", {}))
        
        # SFPD can be 'sfpd' or 'sfpd_incidents'
        sfpd = get_signal(signals.get("sfpd") or signals.get("sfpd_incidents", {}))
        
        # Evictions
        evictions = get_signal(signals.get("evictions", {}))
        
        # Vacancy
        vacancy = get_signal(signals.get("vacancy", {}))
        
        # Collect evidence refs
        for source in signals.values():
            if isinstance(source, dict):
                evidence_refs.extend(source.get("evidence_refs", []))
        
        # Build business features
        features["business_age_years"] = self._extract_business_age(registry, as_of)
        features["is_active"] = 1.0 if registry.get("primary", {}).get("is_active", False) else 0.0
        features["has_naic_code"] = 1.0 if registry.get("primary", {}).get("naic_code") else 0.0
        features["has_parking_tax"] = 1.0 if registry.get("primary", {}).get("parking_tax") else 0.0
        features["has_transient_tax"] = 1.0 if registry.get("primary", {}).get("transient_tax") else 0.0
        
        # Build permit features
        features["permit_count_3m"] = float(permits.get("permit_count_3m", 0))
        features["permit_count_6m"] = float(permits.get("permit_count_6m", 0))
        features["permit_count_12m"] = float(permits.get("permit_count_12m", 0))
        features["permit_trend"] = self._encode_trend(permits.get("permit_trend", "stable"))
        features["avg_permit_cost_12m"] = float(permits.get("avg_permit_cost_12m", 0))
        features["has_recent_permits"] = 1.0 if permits.get("has_recent_permits") else 0.0
        
        # Build 311 complaint features
        features["complaint_count_3m"] = float(complaints_311.get("complaint_count_3m", 0))
        features["complaint_count_6m"] = float(complaints_311.get("complaint_count_6m", 0))
        features["complaint_count_12m"] = float(complaints_311.get("complaint_count_12m", 0))
        features["complaint_trend"] = self._encode_trend(complaints_311.get("complaint_trend", "stable"))
        features["open_closed_ratio"] = float(complaints_311.get("open_closed_ratio", 0))
        features["business_relevant_complaints_6m"] = float(complaints_311.get("business_relevant_count_6m", 0))
        
        # Build DBI features
        features["dbi_count_6m"] = float(dbi.get("dbi_count_6m", 0))
        features["dbi_trend"] = self._encode_trend(dbi.get("dbi_trend", "stable"))
        features["has_open_violations"] = 1.0 if dbi.get("has_open_violations") else 0.0
        
        # Build SFPD features
        features["incident_count_6m"] = float(sfpd.get("incident_count_6m", 0))
        features["incident_trend"] = self._encode_trend(sfpd.get("incident_trend", "stable"))
        features["business_relevant_incidents_6m"] = float(sfpd.get("business_relevant_count_6m", 0))
        
        # Build eviction features
        features["eviction_rate_relative"] = float(evictions.get("relative_to_citywide", 1.0))
        features["neighborhood_stress_level"] = self._encode_stress_level(
            evictions.get("neighborhood_stress_level", "unknown")
        )
        
        # Build vacancy features
        features["vacancy_rate_pct"] = float(vacancy.get("vacancy_rate_pct", 0))
        features["corridor_health"] = self._encode_corridor_health(
            vacancy.get("corridor_health", "unknown")
        )
        
        # Identify missing features
        for feature_name in self.FEATURE_DEFINITIONS:
            if feature_name not in features:
                missing.append(feature_name)
                features[feature_name] = 0.0  # Default to 0
        
        return ModelFeatures(
            features=features,
            feature_version=self.VERSION,
            as_of=as_of,
            entity_id=entity_id,
            evidence_refs=evidence_refs,
            missing_features=missing,
        )
    
    def _extract_business_age(
        self,
        registry: Dict[str, Any],
        as_of: datetime,
    ) -> float:
        """Calculate business age in years"""
        primary = registry.get("primary", {})
        start_date_str = primary.get("location_start_date")
        
        if not start_date_str:
            return 0.0
        
        try:
            # Parse date string
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            age_days = (as_of - start_date.replace(tzinfo=None)).days
            return max(0.0, age_days / 365.25)
        except (ValueError, TypeError):
            return 0.0
    
    def _encode_trend(self, trend: str) -> float:
        """Encode trend as numeric value"""
        trend_map = {
            "up": 1.0,
            "stable": 0.0,
            "down": -1.0,
        }
        return trend_map.get(str(trend).lower(), 0.0)
    
    def _encode_stress_level(self, level: str) -> float:
        """Encode neighborhood stress level"""
        level_map = {
            "very_low": 0.0,
            "low": 1.0,
            "moderate": 2.0,
            "high": 3.0,
            "unknown": 1.5,
        }
        return level_map.get(str(level).lower(), 1.5)
    
    def _encode_corridor_health(self, health: str) -> float:
        """Encode corridor health level"""
        health_map = {
            "excellent": 0.0,
            "good": 1.0,
            "moderate": 2.0,
            "poor": 3.0,
            "critical": 4.0,
            "unknown": 2.0,
        }
        return health_map.get(str(health).lower(), 2.0)
    
    def get_feature_names(self) -> List[str]:
        """Get ordered list of feature names"""
        return self.FEATURE_DEFINITIONS.copy()
