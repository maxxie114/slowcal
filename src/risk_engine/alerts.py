"""
Risk alert system for business failure warnings
"""

import pandas as pd
from typing import List, Dict
from utils.config import Config
import logging

logger = logging.getLogger(__name__)

class RiskAlertSystem:
    """System for generating and managing risk alerts"""
    
    def __init__(self):
        self.alerts = []
    
    def generate_alerts(self, predictions_df: pd.DataFrame) -> List[Dict]:
        """
        Generate alerts based on risk predictions
        
        Args:
            predictions_df: DataFrame with risk predictions
        
        Returns:
            List of alert dictionaries
        """
        alerts = []
        
        high_risk = predictions_df[predictions_df['risk_score'] >= Config.RISK_THRESHOLD_HIGH]
        medium_risk = predictions_df[
            (predictions_df['risk_score'] >= Config.RISK_THRESHOLD_MEDIUM) &
            (predictions_df['risk_score'] < Config.RISK_THRESHOLD_HIGH)
        ]
        
        for _, row in high_risk.iterrows():
            alerts.append({
                'business_name': row.get('business_name', 'Unknown'),
                'risk_level': 'High',
                'risk_score': row['risk_score'],
                'message': self._generate_alert_message(row, 'High'),
                'recommendations': self._generate_recommendations(row)
            })
        
        for _, row in medium_risk.iterrows():
            alerts.append({
                'business_name': row.get('business_name', 'Unknown'),
                'risk_level': 'Medium',
                'risk_score': row['risk_score'],
                'message': self._generate_alert_message(row, 'Medium'),
                'recommendations': self._generate_recommendations(row)
            })
        
        self.alerts = alerts
        logger.info(f"Generated {len(alerts)} alerts")
        return alerts
    
    def _generate_alert_message(self, row: pd.Series, risk_level: str) -> str:
        """Generate alert message based on risk factors"""
        factors = []
        
        if row.get('is_active') == False:
            factors.append("business closure")
        
        if row.get('open_complaints', 0) > 0:
            factors.append(f"{int(row['open_complaints'])} open complaints")
        
        if row.get('complaint_rate', 0) > 0.3:
            factors.append("high complaint rate")
        
        if row.get('total_permits', 0) == 0 and row.get('business_age', 0) > 5:
            factors.append("lack of recent activity")
        
        if factors:
            factor_text = ", ".join(factors)
            return f"{risk_level} risk detected: {factor_text}"
        else:
            return f"{risk_level} risk detected based on business profile"
    
    def _generate_recommendations(self, row: pd.Series) -> List[str]:
        """Generate recommendations to reduce risk"""
        recommendations = []
        
        if row.get('open_complaints', 0) > 0:
            recommendations.append("Address open code enforcement complaints immediately")
        
        if row.get('total_permits', 0) == 0:
            recommendations.append("Consider applying for permits to show business activity")
        
        if row.get('complaint_rate', 0) > 0.3:
            recommendations.append("Review business operations to reduce complaint frequency")
        
        if row.get('is_active') == False:
            recommendations.append("Consider renewing business license and location registration")
        
        if not recommendations:
            recommendations.append("Monitor business metrics closely and maintain compliance")
        
        return recommendations
    
    def get_alerts_summary(self) -> Dict:
        """Get summary statistics of alerts"""
        if not self.alerts:
            return {
                'total_alerts': 0,
                'high_risk': 0,
                'medium_risk': 0
            }
        
        df = pd.DataFrame(self.alerts)
        return {
            'total_alerts': len(self.alerts),
            'high_risk': len(df[df['risk_level'] == 'High']),
            'medium_risk': len(df[df['risk_level'] == 'Medium'])
        }
