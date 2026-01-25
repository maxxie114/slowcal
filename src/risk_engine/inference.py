"""
Business Risk Inference Module

This module provides functions to predict business failure risk using the trained model.

Input Parameters:
-----------------
- business_age (int): Years since business started (e.g., 5)
- has_naic_code (bool): Whether business has NAIC industry classification code
- has_parking_tax (bool): Whether business pays parking tax
- has_transient_tax (bool): Whether business pays transient occupancy tax
- neighborhood_permits (int): Number of permits in the business's neighborhood
- avg_permit_cost (float): Average permit cost in the neighborhood
- neighborhood_311_cases (int): Number of 311 complaints in the neighborhood

Output:
-------
- risk_score (float): Probability of business closure (0.0 to 1.0)
- risk_level (str): 'Low', 'Medium', or 'High'
"""

import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Union
from dataclasses import dataclass


@dataclass
class BusinessInput:
    """Input parameters for risk prediction"""
    business_age: int  # Years since business started
    has_naic_code: bool = True  # Has industry classification
    has_parking_tax: bool = False  # Pays parking tax
    has_transient_tax: bool = False  # Pays transient occupancy tax (hotels)
    neighborhood_permits: int = 0  # Number of permits in neighborhood
    avg_permit_cost: float = 0.0  # Average permit cost in neighborhood
    neighborhood_311_cases: int = 0  # 311 complaints in neighborhood


@dataclass
class RiskPrediction:
    """Output from risk prediction"""
    risk_score: float  # Probability of closure (0-1)
    risk_level: str  # 'Low', 'Medium', or 'High'
    confidence: float  # Model confidence
    feature_contributions: Dict[str, float]  # Feature importance for this prediction


class RiskInference:
    """
    Risk prediction inference engine.
    
    Usage:
    ------
    >>> from risk_engine.inference import RiskInference, BusinessInput
    >>> 
    >>> # Load the model
    >>> engine = RiskInference()
    >>> 
    >>> # Create input
    >>> business = BusinessInput(
    ...     business_age=3,
    ...     has_naic_code=False,
    ...     neighborhood_permits=500,
    ...     avg_permit_cost=50000.0,
    ...     neighborhood_311_cases=200
    ... )
    >>> 
    >>> # Get prediction
    >>> result = engine.predict(business)
    >>> print(f"Risk Score: {result.risk_score:.2f}")
    >>> print(f"Risk Level: {result.risk_level}")
    """
    
    # Risk thresholds
    LOW_THRESHOLD = 0.4
    HIGH_THRESHOLD = 0.7
    
    # Feature order (must match training)
    FEATURE_ORDER = [
        'business_age',
        'has_naic_code',
        'has_parking_tax',
        'has_transient_tax',
        'neighborhood_permits',
        'avg_permit_cost',
        'neighborhood_311_cases'
    ]
    
    def __init__(self, model_path: Optional[Path] = None):
        """
        Initialize the inference engine.
        
        Args:
            model_path: Path to the trained model file. 
                       Defaults to models/risk_model_v1.joblib
        """
        if model_path is None:
            # Default path relative to this file
            model_path = Path(__file__).parent.parent.parent / 'models' / 'risk_model_v1.joblib'
        
        self.model_path = Path(model_path)
        self._load_model()
    
    def _load_model(self):
        """Load the trained model from disk"""
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model not found at {self.model_path}. "
                "Please train the model first using the exploration notebook."
            )
        
        model_data = joblib.load(self.model_path)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.feature_names = model_data['feature_names']
        self.roc_auc = model_data.get('roc_auc', None)
        
        print(f"Model loaded from {self.model_path}")
        if self.roc_auc:
            print(f"Model ROC-AUC: {self.roc_auc:.3f}")
    
    def _prepare_features(self, business: BusinessInput) -> np.ndarray:
        """Convert BusinessInput to feature array"""
        features = pd.DataFrame([{
            'business_age': business.business_age,
            'has_naic_code': int(business.has_naic_code),
            'has_parking_tax': int(business.has_parking_tax),
            'has_transient_tax': int(business.has_transient_tax),
            'neighborhood_permits': business.neighborhood_permits,
            'avg_permit_cost': business.avg_permit_cost,
            'neighborhood_311_cases': business.neighborhood_311_cases
        }])
        
        return self.scaler.transform(features)
    
    def _classify_risk(self, score: float) -> str:
        """Convert risk score to risk level"""
        if score < self.LOW_THRESHOLD:
            return 'Low'
        elif score < self.HIGH_THRESHOLD:
            return 'Medium'
        else:
            return 'High'
    
    def predict(self, business: BusinessInput) -> RiskPrediction:
        """
        Predict risk for a single business.
        
        Args:
            business: BusinessInput with business parameters
        
        Returns:
            RiskPrediction with risk score, level, and feature contributions
        """
        # Prepare features
        X = self._prepare_features(business)
        
        # Get prediction
        risk_score = self.model.predict_proba(X)[0, 1]
        risk_level = self._classify_risk(risk_score)
        
        # Calculate confidence (distance from 0.5)
        confidence = abs(risk_score - 0.5) * 2  # Scale to 0-1
        
        # Get feature contributions (simplified - using feature importance)
        feature_importances = self.model.feature_importances_
        feature_contributions = {
            name: float(importance) 
            for name, importance in zip(self.feature_names, feature_importances)
        }
        
        return RiskPrediction(
            risk_score=float(risk_score),
            risk_level=risk_level,
            confidence=float(confidence),
            feature_contributions=feature_contributions
        )
    
    def predict_batch(self, businesses: list[BusinessInput]) -> list[RiskPrediction]:
        """
        Predict risk for multiple businesses.
        
        Args:
            businesses: List of BusinessInput objects
        
        Returns:
            List of RiskPrediction objects
        """
        return [self.predict(b) for b in businesses]
    
    def predict_from_dict(self, data: Dict) -> RiskPrediction:
        """
        Predict risk from a dictionary of parameters.
        
        Args:
            data: Dictionary with keys matching BusinessInput fields
        
        Returns:
            RiskPrediction
        
        Example:
            >>> engine.predict_from_dict({
            ...     'business_age': 5,
            ...     'has_naic_code': True,
            ...     'neighborhood_permits': 1000
            ... })
        """
        business = BusinessInput(
            business_age=data.get('business_age', 0),
            has_naic_code=data.get('has_naic_code', True),
            has_parking_tax=data.get('has_parking_tax', False),
            has_transient_tax=data.get('has_transient_tax', False),
            neighborhood_permits=data.get('neighborhood_permits', 0),
            avg_permit_cost=data.get('avg_permit_cost', 0.0),
            neighborhood_311_cases=data.get('neighborhood_311_cases', 0)
        )
        return self.predict(business)
    
    def get_model_info(self) -> Dict:
        """Get information about the loaded model"""
        return {
            'model_path': str(self.model_path),
            'model_type': type(self.model).__name__,
            'feature_names': self.feature_names,
            'roc_auc': self.roc_auc,
            'risk_thresholds': {
                'low': f'< {self.LOW_THRESHOLD}',
                'medium': f'{self.LOW_THRESHOLD} - {self.HIGH_THRESHOLD}',
                'high': f'>= {self.HIGH_THRESHOLD}'
            }
        }


def predict_risk(
    business_age: int,
    has_naic_code: bool = True,
    has_parking_tax: bool = False,
    has_transient_tax: bool = False,
    neighborhood_permits: int = 0,
    avg_permit_cost: float = 0.0,
    neighborhood_311_cases: int = 0,
    model_path: Optional[str] = None
) -> Dict:
    """
    Simple function to predict business risk.
    
    This is a convenience function that loads the model and makes a prediction
    in a single call. For batch predictions, use RiskInference class directly.
    
    Args:
        business_age: Years since business started
        has_naic_code: Whether business has NAIC code
        has_parking_tax: Whether business pays parking tax
        has_transient_tax: Whether business pays transient tax
        neighborhood_permits: Number of permits in neighborhood
        avg_permit_cost: Average permit cost in neighborhood
        neighborhood_311_cases: Number of 311 cases in neighborhood
        model_path: Optional path to model file
    
    Returns:
        Dictionary with 'risk_score', 'risk_level', and 'confidence'
    
    Example:
        >>> result = predict_risk(business_age=2, has_naic_code=False)
        >>> print(f"Risk: {result['risk_level']} ({result['risk_score']:.2%})")
    """
    engine = RiskInference(model_path=Path(model_path) if model_path else None)
    
    business = BusinessInput(
        business_age=business_age,
        has_naic_code=has_naic_code,
        has_parking_tax=has_parking_tax,
        has_transient_tax=has_transient_tax,
        neighborhood_permits=neighborhood_permits,
        avg_permit_cost=avg_permit_cost,
        neighborhood_311_cases=neighborhood_311_cases
    )
    
    prediction = engine.predict(business)
    
    return {
        'risk_score': prediction.risk_score,
        'risk_level': prediction.risk_level,
        'confidence': prediction.confidence,
        'feature_contributions': prediction.feature_contributions
    }


# CLI interface
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Predict business failure risk')
    parser.add_argument('--age', type=int, required=True, help='Business age in years')
    parser.add_argument('--naic', type=bool, default=True, help='Has NAIC code')
    parser.add_argument('--parking-tax', type=bool, default=False, help='Pays parking tax')
    parser.add_argument('--transient-tax', type=bool, default=False, help='Pays transient tax')
    parser.add_argument('--permits', type=int, default=0, help='Neighborhood permits')
    parser.add_argument('--permit-cost', type=float, default=0.0, help='Avg permit cost')
    parser.add_argument('--complaints', type=int, default=0, help='Neighborhood 311 cases')
    parser.add_argument('--model', type=str, default=None, help='Path to model file')
    
    args = parser.parse_args()
    
    result = predict_risk(
        business_age=args.age,
        has_naic_code=args.naic,
        has_parking_tax=args.parking_tax,
        has_transient_tax=args.transient_tax,
        neighborhood_permits=args.permits,
        avg_permit_cost=args.permit_cost,
        neighborhood_311_cases=args.complaints,
        model_path=args.model
    )
    
    print("\n" + "="*50)
    print("BUSINESS RISK PREDICTION")
    print("="*50)
    print(f"Risk Score: {result['risk_score']:.2%}")
    print(f"Risk Level: {result['risk_level']}")
    print(f"Confidence: {result['confidence']:.2%}")
    print("\nTop Risk Factors:")
    for feature, importance in sorted(
        result['feature_contributions'].items(), 
        key=lambda x: x[1], 
        reverse=True
    )[:3]:
        print(f"  - {feature}: {importance:.1%}")
    print("="*50)
