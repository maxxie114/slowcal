"""
Fee analysis for city permits and licenses
"""

import pandas as pd
from typing import Dict, List, Optional
from utils.config import Config
import logging

logger = logging.getLogger(__name__)

class FeeAnalyzer:
    """Analyze city fees and identify waiver opportunities"""
    
    def __init__(self):
        # Common SF business fees (these would come from actual fee schedules)
        self.fee_schedule = {
            'business_registration': 150,
            'business_license_renewal': 100,
            'building_permit_base': 500,
            'planning_review': 1000,
            'health_permit': 200,
            'fire_inspection': 150,
            'sign_permit': 300,
            'parking_permit': 50
        }
        
        # Fee waiver eligibility criteria
        self.waiver_eligibility = {
            'small_business': {'threshold': 50000, 'discount': 0.5},
            'nonprofit': {'threshold': None, 'discount': 1.0},
            'low_income': {'threshold': 30000, 'discount': 0.75},
            'new_business': {'threshold': 1, 'discount': 0.25}  # Years
        }
    
    def analyze_fees(
        self,
        business_type: str,
        required_permits: List[str],
        business_info: Optional[Dict] = None
    ) -> Dict:
        """
        Analyze total fees for a business
        
        Args:
            business_type: Type of business
            required_permits: List of required permits/licenses
            business_info: Optional business information for eligibility
        
        Returns:
            Dictionary with fee analysis
        """
        total_fees = 0
        fee_breakdown = {}
        
        for permit in required_permits:
            fee = self.fee_schedule.get(permit.lower().replace(' ', '_'), 0)
            fee_breakdown[permit] = fee
            total_fees += fee
        
        # Check for waivers
        waivers = self._check_waiver_eligibility(business_info, total_fees)
        
        # Calculate final fees after waivers
        final_fees = total_fees
        waiver_savings = 0
        
        for waiver in waivers:
            if waiver['eligible']:
                discount = waiver['discount']
                savings = total_fees * discount
                waiver_savings += savings
                final_fees -= savings
        
        return {
            'total_fees': total_fees,
            'fee_breakdown': fee_breakdown,
            'waiver_opportunities': waivers,
            'waiver_savings': waiver_savings,
            'final_fees_after_waivers': final_fees,
            'required_permits': required_permits,
            'recommendations': self._generate_fee_recommendations(waivers, total_fees)
        }
    
    def _check_waiver_eligibility(
        self,
        business_info: Optional[Dict],
        total_fees: float
    ) -> List[Dict]:
        """Check eligibility for various fee waivers"""
        waivers = []
        
        if not business_info:
            return waivers
        
        # Small business waiver
        revenue = business_info.get('annual_revenue', 0)
        if revenue < self.waiver_eligibility['small_business']['threshold']:
            waivers.append({
                'type': 'Small Business Fee Reduction',
                'eligible': True,
                'discount': self.waiver_eligibility['small_business']['discount'],
                'description': f'Business with revenue < ${self.waiver_eligibility["small_business"]["threshold"]:,} eligible for 50% fee reduction',
                'action_required': 'Submit small business certification'
            })
        else:
            waivers.append({
                'type': 'Small Business Fee Reduction',
                'eligible': False,
                'description': f'Revenue exceeds threshold of ${self.waiver_eligibility["small_business"]["threshold"]:,}'
            })
        
        # Nonprofit waiver
        if business_info.get('is_nonprofit', False):
            waivers.append({
                'type': 'Nonprofit Fee Waiver',
                'eligible': True,
                'discount': self.waiver_eligibility['nonprofit']['discount'],
                'description': 'Nonprofit organizations eligible for full fee waiver',
                'action_required': 'Submit 501(c)(3) documentation'
            })
        else:
            waivers.append({
                'type': 'Nonprofit Fee Waiver',
                'eligible': False,
                'description': 'Not a registered nonprofit'
            })
        
        # New business waiver
        years_in_business = business_info.get('years_in_business', 10)
        if years_in_business <= self.waiver_eligibility['new_business']['threshold']:
            waivers.append({
                'type': 'New Business Fee Reduction',
                'eligible': True,
                'discount': self.waiver_eligibility['new_business']['discount'],
                'description': 'New businesses (1 year or less) eligible for 25% fee reduction',
                'action_required': 'Submit business start date documentation'
            })
        else:
            waivers.append({
                'type': 'New Business Fee Reduction',
                'eligible': False,
                'description': 'Business established for more than 1 year'
            })
        
        return waivers
    
    def _generate_fee_recommendations(
        self,
        waivers: List[Dict],
        total_fees: float
    ) -> List[str]:
        """Generate recommendations for fee optimization"""
        recommendations = []
        
        eligible_waivers = [w for w in waivers if w.get('eligible', False)]
        
        if eligible_waivers:
            recommendations.append(f"Apply for {len(eligible_waivers)} fee waiver(s) to save money")
            for waiver in eligible_waivers:
                recommendations.append(f"- {waiver['type']}: {waiver.get('action_required', 'Submit application')}")
        else:
            recommendations.append("No fee waivers currently eligible - review eligibility criteria annually")
        
        recommendations.extend([
            "Bundle permit applications to reduce processing time",
            "Apply for permits during off-peak seasons if possible",
            "Review fee schedule annually for changes",
            "Consider phased approach for large projects"
        ])
        
        return recommendations
    
    def compare_fee_scenarios(
        self,
        scenario1: Dict,
        scenario2: Dict
    ) -> Dict:
        """
        Compare two fee scenarios
        
        Args:
            scenario1: First fee scenario
            scenario2: Second fee scenario
        
        Returns:
            Comparison analysis
        """
        savings = scenario1['final_fees_after_waivers'] - scenario2['final_fees_after_waivers']
        
        return {
            'scenario1_total': scenario1['final_fees_after_waivers'],
            'scenario2_total': scenario2['final_fees_after_waivers'],
            'difference': savings,
            'percent_savings': (savings / scenario1['final_fees_after_waivers'] * 100) if scenario1['final_fees_after_waivers'] > 0 else 0,
            'recommended_scenario': 'scenario2' if savings > 0 else 'scenario1'
        }
    
    def get_fee_timeline(
        self,
        required_permits: List[str]
    ) -> Dict:
        """
        Get estimated timeline for permit processing
        
        Args:
            required_permits: List of required permits
        
        Returns:
            Timeline information
        """
        # Typical processing times (in business days)
        processing_times = {
            'business_registration': 5,
            'business_license_renewal': 3,
            'building_permit_base': 30,
            'planning_review': 45,
            'health_permit': 10,
            'fire_inspection': 7,
            'sign_permit': 14,
            'parking_permit': 3
        }
        
        timelines = {}
        max_time = 0
        
        for permit in required_permits:
            time = processing_times.get(permit.lower().replace(' ', '_'), 15)
            timelines[permit] = time
            max_time = max(max_time, time)
        
        return {
            'individual_timelines': timelines,
            'estimated_total_days': max_time,
            'estimated_total_weeks': max_time / 5,
            'recommendation': 'Apply for permits in parallel when possible to reduce total time'
        }
