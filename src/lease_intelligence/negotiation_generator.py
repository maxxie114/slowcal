"""
AI-powered negotiation strategy generator using Nemotron
"""

from typing import Dict, List
from utils.nemotron_client import NemotronClient
import logging

logger = logging.getLogger(__name__)

class NegotiationStrategyGenerator:
    """Generate AI-powered negotiation strategies"""
    
    def __init__(self, nemotron_client: NemotronClient = None):
        self.client = nemotron_client or NemotronClient()
    
    def generate_strategy(
        self,
        business_info: Dict,
        lease_info: Dict,
        market_analysis: Dict
    ) -> Dict:
        """
        Generate negotiation strategy using AI
        
        Args:
            business_info: Business information
            lease_info: Current/proposed lease information
            market_analysis: Market analysis results
        
        Returns:
            Dictionary with negotiation strategy
        """
        prompt = self._create_negotiation_prompt(business_info, lease_info, market_analysis)
        
        system_prompt = """You are an expert commercial real estate negotiation advisor specializing 
        in helping small businesses in San Francisco negotiate favorable lease terms. Provide 
        practical, actionable advice based on market conditions and business needs."""
        
        strategy_text = self.client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=1500,
            temperature=0.7
        )
        
        return {
            'strategy': strategy_text,
            'key_points': self._extract_key_points(strategy_text),
            'talking_points': self._generate_talking_points(business_info, market_analysis),
            'concessions_to_request': self._suggest_concessions(lease_info, market_analysis)
        }
    
    def _create_negotiation_prompt(
        self,
        business_info: Dict,
        lease_info: Dict,
        market_analysis: Dict
    ) -> str:
        """Create prompt for negotiation strategy generation"""
        return f"""Generate a comprehensive lease negotiation strategy for a small business in San Francisco.

Business Information:
- Name: {business_info.get('name', 'Unknown')}
- Type: {business_info.get('type', 'Unknown')}
- Location: {business_info.get('neighborhood', 'Unknown')}
- Years in business: {business_info.get('years_in_business', 'Unknown')}

Current/Proposed Lease:
- Square footage: {lease_info.get('square_feet', 'Unknown')}
- Current rent: ${lease_info.get('rent', 'Unknown')}/month
- Rent per sqft: ${lease_info.get('rent_per_sqft', 'Unknown')}/sqft/year
- Lease term: {lease_info.get('term_length', 'Unknown')}

Market Analysis:
- Neighborhood: {market_analysis.get('neighborhood', 'Unknown')}
- Business density: {market_analysis.get('business_density', 'Unknown')}
- Competition level: {market_analysis.get('competition_level', 'Unknown')}

Provide a detailed negotiation strategy including:
1. Recommended negotiation approach
2. Key leverage points
3. Specific terms to negotiate
4. Fallback positions
5. Timeline and tactics"""
    
    def _extract_key_points(self, strategy_text: str) -> List[str]:
        """Extract key points from strategy (simple extraction)"""
        # In a more sophisticated implementation, would use NLP to extract structured points
        lines = strategy_text.split('\n')
        key_points = []
        
        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or 
                        line[0].isdigit() or line.startswith('1.') or line.startswith('2.')):
                key_points.append(line)
        
        return key_points[:10]  # Return top 10 points
    
    def _generate_talking_points(
        self,
        business_info: Dict,
        market_analysis: Dict
    ) -> List[str]:
        """Generate talking points for negotiations"""
        points = []
        
        if business_info.get('years_in_business', 0) > 5:
            points.append("Long-term tenant with proven track record")
        
        if market_analysis.get('competition_level') == 'Low':
            points.append("Limited competition in the area - landlord should value stable tenant")
        
        if market_analysis.get('business_density') == 'High':
            points.append("High business density indicates strong location value")
        
        points.extend([
            "Requesting market-rate adjustments based on comparable properties",
            "Long-term lease commitment in exchange for favorable terms",
            "Good payment history and business stability"
        ])
        
        return points
    
    def _suggest_concessions(
        self,
        lease_info: Dict,
        market_analysis: Dict
    ) -> List[str]:
        """Suggest concessions to request"""
        concessions = [
            "Rent reduction of 5-10%",
            "Free rent period (1-3 months)",
            "Tenant improvement allowance",
            "Reduced security deposit",
            "Flexible sublease/assignment rights",
            "Option to renew at predetermined rate",
            "Maintenance responsibility clarification",
            "Parking space inclusion"
        ]
        
        return concessions
    
    def generate_counter_proposal(
        self,
        landlord_proposal: Dict,
        business_needs: Dict
    ) -> Dict:
        """
        Generate counter-proposal to landlord's offer
        
        Args:
            landlord_proposal: Landlord's initial proposal
            business_needs: Business requirements and constraints
        
        Returns:
            Counter-proposal dictionary
        """
        prompt = f"""Generate a professional counter-proposal to a landlord's lease offer.

Landlord Proposal:
- Rent: ${landlord_proposal.get('rent', 'Unknown')}/month
- Term: {landlord_proposal.get('term', 'Unknown')}
- Security deposit: ${landlord_proposal.get('security_deposit', 'Unknown')}
- Additional terms: {landlord_proposal.get('other_terms', 'None')}

Business Needs:
- Budget: ${business_needs.get('max_budget', 'Unknown')}/month
- Required term: {business_needs.get('min_term', 'Unknown')}
- Must-haves: {business_needs.get('must_haves', 'None')}

Create a professional counter-proposal that:
1. Acknowledges the landlord's offer
2. Proposes alternative terms
3. Justifies the counter-offer
4. Maintains a collaborative tone"""
        
        system_prompt = "You are a professional commercial real estate negotiator helping small businesses."
        
        counter_text = self.client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=1000,
            temperature=0.6
        )
        
        return {
            'counter_proposal': counter_text,
            'suggested_rent': landlord_proposal.get('rent', 0) * 0.9,  # 10% reduction
            'suggested_terms': {
                'rent_reduction': '10%',
                'free_rent_months': 2,
                'security_deposit_reduction': '25%'
            }
        }
