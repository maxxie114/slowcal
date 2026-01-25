"""
Risk prediction model for business failure risk
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score
import joblib
from pathlib import Path
from utils.config import Config
import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)

class RiskPredictor:
    """ML model to predict business failure risk"""
    
    def __init__(self, model_type: str = "random_forest"):
        """
        Initialize risk predictor
        
        Args:
            model_type: 'random_forest' or 'gradient_boosting'
        """
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []
        self.is_trained = False
        
        if model_type == "random_forest":
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                class_weight='balanced'
            )
        elif model_type == "gradient_boosting":
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                random_state=42
            )
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare features for risk prediction
        
        Args:
            df: Business data DataFrame
        
        Returns:
            DataFrame with feature columns
        """
        features = pd.DataFrame()
        
        # Business age
        if 'business_start_year' in df.columns:
            current_year = pd.Timestamp.now().year
            features['business_age'] = current_year - df['business_start_year'].fillna(current_year)
        else:
            features['business_age'] = 0
        
        # Location status
        features['is_active'] = df.get('is_active', False).astype(int)
        features['has_location'] = df.get('has_location', False).astype(int)
        
        # Permit activity
        features['total_permits'] = df.get('total_permits', 0).fillna(0)
        features['has_permits'] = df.get('has_permits', False).astype(int)
        
        # Complaint history
        features['total_complaints'] = df.get('total_complaints', 0).fillna(0)
        features['open_complaints'] = df.get('open_complaints', 0).fillna(0)
        features['has_complaints'] = df.get('has_complaints', False).astype(int)
        features['complaint_rate'] = df.get('complaint_rate', 0).fillna(0)
        
        # Permit costs (if available)
        features['total_permit_cost'] = df.get('total_permit_cost', 0).fillna(0)
        features['avg_permit_cost'] = df.get('avg_permit_cost', 0).fillna(0)
        
        # Fill any remaining NaN
        features = features.fillna(0)
        
        self.feature_names = features.columns.tolist()
        return features
    
    def create_target(self, df: pd.DataFrame) -> pd.Series:
        """
        Create target variable (business failure indicator)
        
        Uses heuristics:
        - Business closed (location_end_date exists)
        - No recent activity
        - High complaint rate
        
        Args:
            df: Business data DataFrame
        
        Returns:
            Series with binary target (1 = high risk, 0 = low risk)
        """
        target = pd.Series(0, index=df.index)
        
        # Business closed
        if 'is_active' in df.columns:
            target[df['is_active'] == False] = 1
        
        # High complaint rate
        if 'complaint_rate' in df.columns:
            target[df['complaint_rate'] > 0.5] = 1
        
        # Old business with no recent permits
        if 'business_start_year' in df.columns and 'total_permits' in df.columns:
            current_year = pd.Timestamp.now().year
            old_business = (current_year - df['business_start_year']) > 5
            no_permits = df['total_permits'] == 0
            target[old_business & no_permits] = 1
        
        return target
    
    def train(self, df: pd.DataFrame, test_size: float = 0.2) -> Dict:
        """
        Train the risk prediction model
        
        Args:
            df: Training data DataFrame
            test_size: Proportion of data for testing
        
        Returns:
            Dictionary with training metrics
        """
        logger.info("Preparing features and target...")
        X = self.prepare_features(df)
        y = self.create_target(df)
        
        # Handle class imbalance
        if y.sum() == 0:
            logger.warning("No positive samples found, using synthetic data")
            y.iloc[:min(10, len(y))] = 1
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        logger.info(f"Training {self.model_type} model...")
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        y_pred_proba = self.model.predict_proba(X_test_scaled)[:, 1]
        
        metrics = {
            'roc_auc': roc_auc_score(y_test, y_pred_proba),
            'classification_report': classification_report(y_test, y_pred, output_dict=True)
        }
        
        self.is_trained = True
        logger.info(f"Model trained. ROC-AUC: {metrics['roc_auc']:.3f}")
        
        return metrics
    
    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Predict risk for businesses
        
        Args:
            df: Business data DataFrame
        
        Returns:
            DataFrame with risk predictions
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")
        
        X = self.prepare_features(df)
        X_scaled = self.scaler.transform(X)
        
        risk_proba = self.model.predict_proba(X_scaled)[:, 1]
        risk_class = self.model.predict(X_scaled)
        
        results = df.copy()
        results['risk_score'] = risk_proba
        results['risk_level'] = pd.cut(
            risk_proba,
            bins=[0, Config.RISK_THRESHOLD_MEDIUM, Config.RISK_THRESHOLD_HIGH, 1.0],
            labels=['Low', 'Medium', 'High']
        )
        results['risk_class'] = risk_class
        
        return results
    
    def get_feature_importance(self) -> pd.DataFrame:
        """Get feature importance from trained model"""
        if not self.is_trained:
            raise ValueError("Model must be trained first")
        
        importances = self.model.feature_importances_
        return pd.DataFrame({
            'feature': self.feature_names,
            'importance': importances
        }).sort_values('importance', ascending=False)
    
    def save(self, filepath: Optional[Path] = None):
        """Save model to disk"""
        filepath = filepath or Config.MODELS_DIR / f"risk_model_{Config.RISK_MODEL_VERSION}.joblib"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'model_type': self.model_type
        }, filepath)
        logger.info(f"Model saved to {filepath}")
    
    @classmethod
    def load(cls, filepath: Path):
        """Load model from disk"""
        data = joblib.load(filepath)
        
        predictor = cls(model_type=data['model_type'])
        predictor.model = data['model']
        predictor.scaler = data['scaler']
        predictor.feature_names = data['feature_names']
        predictor.is_trained = True
        
        logger.info(f"Model loaded from {filepath}")
        return predictor
