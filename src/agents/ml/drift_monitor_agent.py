"""
Drift Monitor Agent

Monitors for distribution drift in features and scores.
Detects pipeline regressions and data quality issues.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

import numpy as np

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)


@dataclass
class DriftResult:
    """Result of drift detection for one feature"""
    feature_name: str
    reference_mean: float
    current_mean: float
    reference_std: float
    current_std: float
    psi_score: float  # Population Stability Index
    is_drifted: bool
    drift_type: Optional[str]  # "mean_shift", "variance_change", "distribution_shift"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_name": self.feature_name,
            "reference_mean": self.reference_mean,
            "current_mean": self.current_mean,
            "psi_score": self.psi_score,
            "is_drifted": self.is_drifted,
            "drift_type": self.drift_type,
        }


@dataclass
class DriftReport:
    """Complete drift monitoring report"""
    check_time: datetime
    reference_period: str
    current_period: str
    feature_drifts: List[DriftResult]
    score_drift: Optional[DriftResult]
    overall_health: str  # "healthy", "warning", "critical"
    alerts: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_time": self.check_time.isoformat(),
            "reference_period": self.reference_period,
            "current_period": self.current_period,
            "feature_drifts": [d.to_dict() for d in self.feature_drifts],
            "score_drift": self.score_drift.to_dict() if self.score_drift else None,
            "overall_health": self.overall_health,
            "alerts": self.alerts,
        }


class DriftMonitorAgent:
    """
    Agent for monitoring feature and score drift.
    
    Runs periodically (e.g., weekly) to detect:
    - Feature distribution drift
    - Score distribution drift
    - Join confidence drift
    
    Uses Population Stability Index (PSI) for drift detection.
    
    Example usage:
        agent = DriftMonitorAgent()
        
        # Provide reference and current feature distributions
        report = agent.check_drift(
            reference_features=training_features,
            current_features=recent_features,
            reference_scores=training_scores,
            current_scores=recent_scores,
        )
        
        if report.overall_health == "critical":
            send_alert(report.alerts)
    """
    
    VERSION = "0.1"
    
    # PSI thresholds
    PSI_THRESHOLD_WARNING = 0.1
    PSI_THRESHOLD_CRITICAL = 0.25
    
    @property
    def name(self) -> str:
        return "DriftMonitorAgent"
    
    def check_drift(
        self,
        reference_features: Dict[str, List[float]],
        current_features: Dict[str, List[float]],
        reference_scores: List[float] = None,
        current_scores: List[float] = None,
    ) -> DriftReport:
        """
        Check for drift between reference and current distributions.
        
        Args:
            reference_features: Dict of feature_name -> values for reference period
            current_features: Dict of feature_name -> values for current period
            reference_scores: Optional reference risk scores
            current_scores: Optional current risk scores
        
        Returns:
            DriftReport with drift analysis
        """
        check_time = datetime.utcnow()
        feature_drifts = []
        alerts = []
        
        # Check each feature
        for feature_name in reference_features.keys():
            if feature_name not in current_features:
                continue
            
            ref_values = reference_features[feature_name]
            cur_values = current_features[feature_name]
            
            drift_result = self._check_feature_drift(
                feature_name,
                ref_values,
                cur_values,
            )
            feature_drifts.append(drift_result)
            
            if drift_result.is_drifted:
                alerts.append(
                    f"Feature '{feature_name}' has drifted: "
                    f"PSI={drift_result.psi_score:.3f} ({drift_result.drift_type})"
                )
        
        # Check score drift
        score_drift = None
        if reference_scores and current_scores:
            score_drift = self._check_feature_drift(
                "risk_score",
                reference_scores,
                current_scores,
            )
            if score_drift.is_drifted:
                alerts.append(
                    f"Risk score distribution has drifted: PSI={score_drift.psi_score:.3f}"
                )
        
        # Determine overall health
        critical_count = sum(1 for d in feature_drifts if d.psi_score >= self.PSI_THRESHOLD_CRITICAL)
        warning_count = sum(1 for d in feature_drifts if d.is_drifted)
        
        if critical_count > 0 or (score_drift and score_drift.psi_score >= self.PSI_THRESHOLD_CRITICAL):
            overall_health = "critical"
        elif warning_count > len(feature_drifts) * 0.3:  # >30% features drifted
            overall_health = "warning"
        else:
            overall_health = "healthy"
        
        return DriftReport(
            check_time=check_time,
            reference_period="training",
            current_period="recent",
            feature_drifts=feature_drifts,
            score_drift=score_drift,
            overall_health=overall_health,
            alerts=alerts,
        )
    
    def _check_feature_drift(
        self,
        feature_name: str,
        ref_values: List[float],
        cur_values: List[float],
    ) -> DriftResult:
        """Check drift for a single feature"""
        ref_arr = np.array(ref_values)
        cur_arr = np.array(cur_values)
        
        # Basic statistics
        ref_mean = float(np.mean(ref_arr))
        ref_std = float(np.std(ref_arr))
        cur_mean = float(np.mean(cur_arr))
        cur_std = float(np.std(cur_arr))
        
        # Calculate PSI
        psi_score = self._calculate_psi(ref_arr, cur_arr)
        
        # Determine drift type
        is_drifted = psi_score >= self.PSI_THRESHOLD_WARNING
        drift_type = None
        
        if is_drifted:
            # Check if it's mainly mean shift or variance change
            mean_diff = abs(cur_mean - ref_mean) / (ref_std + 1e-10)
            std_ratio = cur_std / (ref_std + 1e-10)
            
            if mean_diff > 1.0:
                drift_type = "mean_shift"
            elif std_ratio < 0.5 or std_ratio > 2.0:
                drift_type = "variance_change"
            else:
                drift_type = "distribution_shift"
        
        return DriftResult(
            feature_name=feature_name,
            reference_mean=round(ref_mean, 4),
            current_mean=round(cur_mean, 4),
            reference_std=round(ref_std, 4),
            current_std=round(cur_std, 4),
            psi_score=round(psi_score, 4),
            is_drifted=is_drifted,
            drift_type=drift_type,
        )
    
    def _calculate_psi(
        self,
        reference: np.ndarray,
        current: np.ndarray,
        n_bins: int = 10,
    ) -> float:
        """
        Calculate Population Stability Index (PSI).
        
        PSI = Σ (Actual% - Expected%) * ln(Actual% / Expected%)
        
        PSI < 0.1: No significant change
        0.1 <= PSI < 0.25: Moderate change
        PSI >= 0.25: Significant change
        """
        # Create bins based on reference distribution
        min_val = min(reference.min(), current.min())
        max_val = max(reference.max(), current.max())
        
        if min_val == max_val:
            return 0.0
        
        bin_edges = np.linspace(min_val, max_val, n_bins + 1)
        
        # Calculate proportions
        ref_counts, _ = np.histogram(reference, bins=bin_edges)
        cur_counts, _ = np.histogram(current, bins=bin_edges)
        
        # Convert to proportions with small epsilon to avoid division by zero
        epsilon = 1e-10
        ref_props = ref_counts / len(reference) + epsilon
        cur_props = cur_counts / len(current) + epsilon
        
        # Calculate PSI
        psi = np.sum((cur_props - ref_props) * np.log(cur_props / ref_props))
        
        return float(psi)
    
    def check_join_confidence_drift(
        self,
        reference_confidences: List[float],
        current_confidences: List[float],
    ) -> DriftResult:
        """
        Check for drift in entity resolution confidence.
        
        Lower confidence over time might indicate data quality issues.
        """
        return self._check_feature_drift(
            "join_confidence",
            reference_confidences,
            current_confidences,
        )
    
    def get_monitoring_schedule(self) -> Dict[str, Any]:
        """Get recommended monitoring schedule"""
        return {
            "drift_check_frequency": "weekly",
            "recommended_day": "Monday",
            "recommended_time": "06:00 UTC",
            "minimum_samples_reference": 1000,
            "minimum_samples_current": 100,
            "alert_channels": ["email", "slack"],
        }
