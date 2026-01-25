"""
Compliance advisor for city regulations and requirements
"""

from typing import Dict, List
from utils.nemotron_client import NemotronClient
import logging

logger = logging.getLogger(__name__)

class ComplianceAdvisor:
    """AI-powered advisor for city compliance requirements"""
    
    def __init__(self, nemotron_client: NemotronClient = None):
        self.client = nemotron_client or NemotronClient()
    
    def get_compliance_requirements(
        self,
        business_type: str,
        location: str,
        business_info: Dict
    ) -> Dict:
        """
        Get compliance requirements for a business
        
        Args:
            business_type: Type of business
            location: Business location/neighborhood
            business_info: Additional business information
        
        Returns:
            Dictionary with compliance requirements
        """
        prompt = f"""Provide compliance requirements for a small business in San Francisco.

Business Information:
- Type: {business_type}
- Location: {location}
- Square footage: {business_info.get('square_feet', 'Unknown')}
- Employees: {business_info.get('num_employees', 'Unknown')}
- Serves food: {business_info.get('serves_food', False)}
- Serves alcohol: {business_info.get('serves_alcohol', False)}

Provide a comprehensive list of:
1. Required permits and licenses
2. Zoning requirements
3. Health department requirements (if applicable)
4. Fire department requirements
5. ADA compliance requirements
6. Labor law requirements
7. Tax obligations
8. Annual renewal requirements

Format as a clear, actionable checklist."""
        
        system_prompt = """You are an expert on San Francisco city regulations and compliance 
        requirements for small businesses. Provide accurate, up-to-date information about permits, 
        licenses, and regulatory requirements."""
        
        requirements_text = self.client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=2000,
            temperature=0.3
        )
        
        return {
            'requirements': requirements_text,
            'checklist': self._parse_checklist(requirements_text),
            'priority_items': self._identify_priority_items(business_type, business_info)
        }
    
    def _parse_checklist(self, text: str) -> List[str]:
        """Parse checklist items from text"""
        lines = text.split('\n')
        checklist = []
        
        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or 
                        line[0].isdigit() or 'required' in line.lower() or 
                        'permit' in line.lower() or 'license' in line.lower()):
                # Clean up the line
                line = line.lstrip('-•0123456789. ')
                if line:
                    checklist.append(line)
        
        return checklist[:20]  # Return top 20 items
    
    def _identify_priority_items(
        self,
        business_type: str,
        business_info: Dict
    ) -> List[str]:
        """Identify high-priority compliance items"""
        priorities = []
        
        # Always required
        priorities.append("Business Registration Certificate")
        priorities.append("Business Tax Certificate")
        
        # Location-specific
        if business_info.get('has_physical_location', True):
            priorities.append("Certificate of Occupancy")
            priorities.append("Zoning Compliance Verification")
        
        # Industry-specific
        if business_info.get('serves_food', False):
            priorities.append("Health Department Permit")
            priorities.append("Food Handler Certification")
        
        if business_info.get('serves_alcohol', False):
            priorities.append("ABC License (Alcohol Beverage Control)")
        
        if business_info.get('has_employees', False):
            priorities.append("Workers' Compensation Insurance")
            priorities.append("Payroll Tax Registration")
        
        # Building-related
        if business_info.get('requires_construction', False):
            priorities.append("Building Permits")
            priorities.append("Planning Department Approval")
        
        return priorities
    
    def check_compliance_status(
        self,
        business_info: Dict,
        current_permits: List[str]
    ) -> Dict:
        """
        Check current compliance status
        
        Args:
            business_info: Business information
            current_permits: List of currently held permits/licenses
        
        Returns:
            Compliance status analysis
        """
        required = self._identify_priority_items(
            business_info.get('business_type', ''),
            business_info
        )
        
        missing = [item for item in required if item not in current_permits]
        compliant = len(missing) == 0
        
        return {
            'is_compliant': compliant,
            'required_items': required,
            'current_items': current_permits,
            'missing_items': missing,
            'compliance_score': (len(current_permits) / len(required) * 100) if required else 0,
            'recommendations': self._generate_compliance_recommendations(missing, business_info)
        }
    
    def _generate_compliance_recommendations(
        self,
        missing_items: List[str],
        business_info: Dict
    ) -> List[str]:
        """Generate recommendations to achieve compliance"""
        recommendations = []
        
        if missing_items:
            recommendations.append(f"Obtain {len(missing_items)} missing permit(s)/license(s) immediately")
            for item in missing_items[:5]:  # Top 5
                recommendations.append(f"- Priority: {item}")
        
        recommendations.extend([
            "Set up calendar reminders for permit renewals",
            "Maintain organized records of all permits and licenses",
            "Review compliance requirements annually",
            "Consider consulting with a business attorney for complex requirements"
        ])
        
        return recommendations
    
    def get_renewal_schedule(
        self,
        current_permits: List[str]
    ) -> Dict:
        """
        Get renewal schedule for permits
        
        Args:
            current_permits: List of current permits
        
        Returns:
            Renewal schedule information
        """
        # Typical renewal periods
        renewal_periods = {
            'Business Registration Certificate': 'Annual',
            'Business Tax Certificate': 'Annual',
            'Health Department Permit': 'Annual',
            'ABC License': 'Annual',
            'Certificate of Occupancy': 'No renewal required',
            'Building Permits': 'Project-specific'
        }
        
        schedule = {}
        for permit in current_permits:
            schedule[permit] = renewal_periods.get(permit, 'Check with issuing department')
        
        return {
            'renewal_schedule': schedule,
            'annual_renewals': [p for p, period in schedule.items() if 'Annual' in period],
            'recommendation': 'Set reminders 60 days before renewal deadlines'
        }
