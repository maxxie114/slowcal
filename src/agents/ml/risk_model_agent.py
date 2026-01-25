"""
Risk Model Agent

Wraps the trained risk prediction model for inference.
Provides deterministic risk scores with feature importance.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

import numpy as np

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.config import Config

logger = logging.getLogger(__name__)

# Try to import joblib for model loading
try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False
    logger.warning("joblib not available - model loading disabled")


@dataclass
class RiskScore:
    """Risk prediction result"""
    score: float  # 0-1 probability
    band: str  # "low", "medium", "high"
    model_version: str
    top_drivers: List[Dict[str, Any]] = field(default_factory=list)
    calibrated: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "band": self.band,
            "model_version": self.model_version,
            "top_drivers": self.top_drivers,
            "calibrated": self.calibrated,
        }


class RiskModelAgent:
    """
    Agent for deterministic risk scoring.
    
    Wraps the trained ML model and provides:
    - Risk score (probability 0-1)
    - Risk band (low/medium/high)
    - Top drivers (feature importance for this prediction)
    
    Example usage:
        agent = RiskModelAgent()
        
        from agents.ml.feature_builder_agent import ModelFeatures
        
        risk = agent.predict(features)
        print(f"Risk: {risk.score:.2f} ({risk.band})")
        for driver in risk.top_drivers:
            print(f"  {driver['driver']}: {driver['direction']}")
    """
    
    VERSION = Config.RISK_MODEL_VERSION
    
    # Feature importance for heuristic model (when trained model not available)
    HEURISTIC_WEIGHTS = {
        "complaint_count_6m": 0.15,
        "business_relevant_complaints_6m": 0.12,
        "has_open_violations": 0.10,
        "dbi_count_6m": 0.10,
        "incident_count_6m": 0.08,
        "business_relevant_incidents_6m": 0.08,
        "vacancy_rate_pct": 0.07,
        "eviction_rate_relative": 0.06,
        "neighborhood_stress_level": 0.05,
        "corridor_health": 0.05,
        "complaint_trend": 0.04,
        "permit_trend": -0.03,  # Negative = more permits is good
        "business_age_years": -0.04,  # Negative = older is better
        "has_recent_permits": -0.03,
    }
    
    def __init__(self, model_path: Path = None):
        self.model_path = model_path or Config.MODELS_DIR / "risk_model_v1.joblib"
        self.model = None
        self.scaler = None
        self.feature_names = None
        
        # Try to load trained model
        self._load_model()
    
    @property
    def name(self) -> str:
        return "RiskModelAgent"
    
    def get_version(self) -> str:
        """Return agent version"""
        return self.VERSION
    
    def _load_model(self) -> None:
        """Load trained model if available"""
        if not JOBLIB_AVAILABLE:
            logger.info("Using heuristic model (joblib not available)")
            return
        
        if not self.model_path.exists():
            logger.info(f"No trained model at {self.model_path}, using heuristic")
            return
        
        try:
            model_data = joblib.load(self.model_path)
            if isinstance(model_data, dict):
                self.model = model_data.get("model")
                self.scaler = model_data.get("scaler")
                self.feature_names = model_data.get("feature_names")
            else:
                self.model = model_data
            logger.info(f"Loaded model from {self.model_path}")
        except Exception as e:
            logger.warning(f"Failed to load model: {e}, using heuristic")
    
    def predict(
        self,
        features: "ModelFeatures",
    ) -> RiskScore:
        """
        Predict risk score from features.
        
        Args:
            features: ModelFeatures from FeatureBuilderAgent
        
        Returns:
            RiskScore with score, band, and top drivers
        """
        if self.model is not None:
            return self._predict_with_model(features)
        else:
            return self._predict_heuristic(features)
    
    def _predict_with_model(self, features: "ModelFeatures") -> RiskScore:
        """Use trained model for prediction"""
        try:
            # Prepare feature array
            if self.feature_names:
                feature_array = features.to_array(self.feature_names)
            else:
                feature_array = list(features.features.values())
            
            X = np.array([feature_array])
            
            # Scale if scaler available
            if self.scaler:
                X = self.scaler.transform(X)
            
            # Predict probability
            if hasattr(self.model, 'predict_proba'):
                proba = self.model.predict_proba(X)[0]
                score = proba[1] if len(proba) > 1 else proba[0]
            else:
                score = float(self.model.predict(X)[0])
            
            # Get feature importances if available
            top_drivers = self._get_model_drivers(features, X)
            
            return RiskScore(
                score=float(score),
                band=self._score_to_band(score),
                model_version=self.VERSION,
                top_drivers=top_drivers,
                calibrated=False,
            )
            
        except Exception as e:
            logger.error(f"Model prediction failed: {e}, falling back to heuristic")
            return self._predict_heuristic(features)
    
    def _predict_heuristic(self, features: "ModelFeatures") -> RiskScore:
        """Use heuristic model when trained model not available"""
        score = 0.3  # Base score
        drivers = []
        
        for feature_name, weight in self.HEURISTIC_WEIGHTS.items():
            value = features.features.get(feature_name, 0.0)
            
            # Normalize value contribution
            if feature_name.endswith("_count_6m") or feature_name.endswith("_count_3m"):
                # Complaints/incidents: normalize by typical range
                normalized = min(value / 50, 1.0)
            elif feature_name == "vacancy_rate_pct":
                normalized = min(value / 20, 1.0)
            elif feature_name == "eviction_rate_relative":
                normalized = min(value / 2, 1.0)
            elif feature_name == "business_age_years":
                # Older is better, cap at 10 years
                normalized = min(value / 10, 1.0)
            else:
                normalized = value
            
            contribution = weight * normalized
            score += contribution
            
            if abs(contribution) > 0.02:  # Only track significant drivers
                drivers.append({
                    "driver": feature_name,
                    "direction": "up" if contribution > 0 else "down",
                    "contribution": round(abs(contribution), 3),
                    "value": value,
                })
        
        # Clamp score to 0-1
        score = max(0.0, min(1.0, score))
        
        # Sort drivers by contribution
        drivers.sort(key=lambda x: x["contribution"], reverse=True)
        
        return RiskScore(
            score=round(score, 3),
            band=self._score_to_band(score),
            model_version=f"{self.VERSION}-heuristic",
            top_drivers=drivers[:5],
            calibrated=False,
        )
    
    def _get_model_drivers(
        self,
        features: "ModelFeatures",
        X: np.ndarray,
    ) -> List[Dict[str, Any]]:
        """Extract top drivers from model"""
        drivers = []
        
        # Try to get feature importances
        importances = None
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
        elif hasattr(self.model, 'coef_'):
            importances = np.abs(self.model.coef_).flatten()
        
        if importances is not None and self.feature_names:
            # Pair features with importances
            paired = list(zip(self.feature_names, importances, X[0]))
            paired.sort(key=lambda x: x[1], reverse=True)
            
            for name, importance, value in paired[:5]:
                drivers.append({
                    "driver": name,
                    "direction": "up" if value > 0 else "stable",
                    "contribution": round(float(importance), 3),
                    "value": float(value),
                })
        
        return drivers
    
    def _score_to_band(self, score: float) -> str:
        """Convert score to risk band"""
        if score >= Config.RISK_THRESHOLD_HIGH:
            return "high"
        elif score >= Config.RISK_THRESHOLD_MEDIUM:
            return "medium"
        else:
            return "low"
    
    def is_trained_model_available(self) -> bool:
        """Check if trained model is loaded"""
        return self.model is not None
