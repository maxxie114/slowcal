"""
Calibration Agent

Applies probability calibration to model outputs.
Ensures predicted probabilities match empirical frequencies.
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import numpy as np

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)


@dataclass
class CalibratedScore:
    """Calibrated risk score"""
    original_score: float
    calibrated_score: float
    calibration_method: str
    adjustment: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_score": self.original_score,
            "calibrated_score": self.calibrated_score,
            "calibration_method": self.calibration_method,
            "adjustment": self.adjustment,
        }


class CalibrationAgent:
    """
    Agent for probability calibration.
    
    Applies calibration to ensure model probabilities
    match observed frequencies (e.g., if model predicts 70%,
    empirically 70% of such cases should be positive).
    
    Supports:
    - Platt scaling (logistic calibration)
    - Isotonic regression
    - Temperature scaling (for neural nets)
    
    Example usage:
        agent = CalibrationAgent()
        calibrated = agent.calibrate(risk_score)
    """
    
    VERSION = "0.1"
    
    def __init__(
        self,
        calibration_params: Dict[str, Any] = None,
    ):
        """
        Initialize with optional pre-fitted calibration parameters.
        
        Args:
            calibration_params: Dict with calibration parameters
                For Platt: {"method": "platt", "A": float, "B": float}
                For isotonic: {"method": "isotonic", "mapping": [(x, y), ...]}
        """
        self.params = calibration_params or {}
        self.method = self.params.get("method", "identity")
    
    @property
    def name(self) -> str:
        return "CalibrationAgent"
    
    def calibrate(
        self,
        score: float,
        method: str = None,
    ) -> CalibratedScore:
        """
        Calibrate a risk score.
        
        Args:
            score: Original probability score (0-1)
            method: Calibration method override
        
        Returns:
            CalibratedScore with original and calibrated values
        """
        method = method or self.method
        
        if method == "platt":
            calibrated = self._platt_calibration(score)
        elif method == "isotonic":
            calibrated = self._isotonic_calibration(score)
        elif method == "temperature":
            calibrated = self._temperature_calibration(score)
        else:
            # Identity (no calibration)
            calibrated = score
        
        return CalibratedScore(
            original_score=score,
            calibrated_score=round(calibrated, 4),
            calibration_method=method,
            adjustment=round(calibrated - score, 4),
        )
    
    def calibrate_batch(
        self,
        scores: List[float],
        method: str = None,
    ) -> List[CalibratedScore]:
        """Calibrate a batch of scores"""
        return [self.calibrate(s, method) for s in scores]
    
    def _platt_calibration(self, score: float) -> float:
        """
        Apply Platt scaling (logistic calibration).
        
        P(y=1|score) = 1 / (1 + exp(A*score + B))
        """
        A = self.params.get("A", -1.0)
        B = self.params.get("B", 0.0)
        
        # Avoid numerical overflow
        logit = A * score + B
        if logit > 20:
            return 0.0
        elif logit < -20:
            return 1.0
        else:
            return 1.0 / (1.0 + np.exp(logit))
    
    def _isotonic_calibration(self, score: float) -> float:
        """
        Apply isotonic regression calibration.
        
        Uses pre-fitted piecewise linear mapping.
        """
        mapping = self.params.get("mapping", [])
        
        if not mapping:
            return score
        
        # Sort mapping by x value
        mapping = sorted(mapping, key=lambda x: x[0])
        
        # Find interpolation interval
        for i in range(len(mapping) - 1):
            x1, y1 = mapping[i]
            x2, y2 = mapping[i + 1]
            
            if x1 <= score <= x2:
                # Linear interpolation
                if x2 == x1:
                    return y1
                t = (score - x1) / (x2 - x1)
                return y1 + t * (y2 - y1)
        
        # Extrapolation
        if score < mapping[0][0]:
            return mapping[0][1]
        else:
            return mapping[-1][1]
    
    def _temperature_calibration(self, score: float) -> float:
        """
        Apply temperature scaling.
        
        Commonly used for neural network calibration.
        Higher temperature = more uncertain predictions.
        """
        temperature = self.params.get("temperature", 1.0)
        
        if temperature <= 0:
            return score
        
        # Convert to logit, scale, convert back
        # Avoid edge cases
        score = max(0.001, min(0.999, score))
        logit = np.log(score / (1 - score))
        scaled_logit = logit / temperature
        
        return 1.0 / (1.0 + np.exp(-scaled_logit))
    
    def fit_platt(
        self,
        scores: List[float],
        labels: List[int],
    ) -> Dict[str, float]:
        """
        Fit Platt scaling parameters from data.
        
        Args:
            scores: Predicted probabilities
            labels: True binary labels
        
        Returns:
            Dict with fitted A and B parameters
        """
        # Simple gradient descent for Platt parameters
        # In production, use sklearn.calibration.CalibratedClassifierCV
        
        scores = np.array(scores)
        labels = np.array(labels)
        
        # Initialize
        A = -1.0
        B = 0.0
        lr = 0.01
        
        for _ in range(1000):
            # Forward pass
            logits = A * scores + B
            probs = 1.0 / (1.0 + np.exp(-logits))
            
            # Gradient
            error = probs - labels
            grad_A = np.mean(error * scores)
            grad_B = np.mean(error)
            
            # Update
            A -= lr * grad_A
            B -= lr * grad_B
        
        self.params = {"method": "platt", "A": float(-A), "B": float(-B)}
        self.method = "platt"
        
        return self.params
    
    def get_reliability_diagram_data(
        self,
        scores: List[float],
        labels: List[int],
        n_bins: int = 10,
    ) -> Dict[str, List[float]]:
        """
        Compute data for reliability diagram (calibration plot).
        
        Returns:
            Dict with bin_midpoints, observed_frequency, predicted_mean
        """
        scores = np.array(scores)
        labels = np.array(labels)
        
        bin_edges = np.linspace(0, 1, n_bins + 1)
        
        midpoints = []
        observed = []
        predicted = []
        
        for i in range(n_bins):
            mask = (scores >= bin_edges[i]) & (scores < bin_edges[i + 1])
            if mask.sum() > 0:
                midpoints.append((bin_edges[i] + bin_edges[i + 1]) / 2)
                observed.append(labels[mask].mean())
                predicted.append(scores[mask].mean())
        
        return {
            "bin_midpoints": midpoints,
            "observed_frequency": observed,
            "predicted_mean": predicted,
        }
