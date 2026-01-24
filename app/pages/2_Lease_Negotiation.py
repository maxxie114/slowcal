"""
Lease Negotiation Intelligence Page
"""

import streamlit as st
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.lease_intelligence.market_analysis import LeaseMarketAnalyzer
from src.lease_intelligence.negotiation_generator import NegotiationStrategyGenerator
from src.utils.nemotron_client import NemotronClient
from src.utils.config import Config

st.set_page_config(
    page_title="Lease Negotiation",
    page_icon="💼",
    layout="wide"
)

st.title("💼 Lease Negotiation Intelligence")
st.markdown("Get AI-powered market analysis and negotiation strategies for your lease")

# Initialize components
market_analyzer = LeaseMarketAnalyzer()
nemotron_client = NemotronClient()
strategy_generator = NegotiationStrategyGenerator(nemotron_client)

# Sidebar for input
with st.sidebar:
    st.header("Business Information")
    business_name = st.text_input("Business Name", placeholder="Your Business Name")
    business_type = st.selectbox(
        "Business Type",
        ["Retail", "Restaurant", "Office", "Manufacturing", "Other"]
    )
    neighborhood = st.text_input("Neighborhood", placeholder="e.g., Mission District, SOMA")
    years_in_business = st.number_input("Years in Business", min_value=0, max_value=50, value=5)

# Main content tabs
tab1, tab2, tab3 = st.tabs(["Market Analysis", "Negotiation Strategy", "Counter-Proposal"])

with tab1:
    st.header("Market Analysis")
    
    if neighborhood:
        if st.button("Analyze Market", type="primary"):
            with st.spinner("Analyzing market conditions..."):
                try:
                    analysis = market_analyzer.analyze_neighborhood(neighborhood, business_type)
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Business Density", analysis['business_density'])
                    col2.metric("Competition Level", analysis['competition_level'])
                    col3.metric("Market Growth", analysis['market_trends']['business_growth'])
                    
                    st.subheader("Market Trends")
                    trends = analysis['market_trends']
                    st.write(f"- **Business Growth:** {trends['business_growth']}")
                    st.write(f"- **Closure Rate:** {trends['closure_rate']}")
                    st.write(f"- **New Openings:** {trends['new_openings']}")
                    
                    st.subheader("Market Recommendations")
                    for rec in analysis['recommendations']:
                        st.write(f"• {rec}")
                    
                    # Comparable rates
                    st.subheader("Comparable Lease Rates")
                    square_feet = st.number_input("Square Footage", min_value=100, value=1000, key="sqft_market")
                    
                    if square_feet:
                        rates = market_analyzer.get_comparable_rates(neighborhood, square_feet)
                        
                        col1, col2 = st.columns(2)
                        col1.metric("Rate per sqft/year", f"${rates['estimated_rate_per_sqft']:.2f}")
                        col2.metric("Estimated Monthly Rent", f"${rates['estimated_monthly_rent']:,.2f}")
                        
                        st.write(f"**Market Range:** ${rates['market_range']['low']:.2f} - ${rates['market_range']['high']:.2f} per sqft/year")
                        st.info(f"ℹ️ {rates['data_quality']}")
                
                except Exception as e:
                    st.error(f"Error analyzing market: {e}")
    else:
        st.info("Enter a neighborhood in the sidebar to get started.")

with tab2:
    st.header("AI-Powered Negotiation Strategy")
    
    st.subheader("Current/Proposed Lease Information")
    col1, col2 = st.columns(2)
    
    with col1:
        square_feet = st.number_input("Square Footage", min_value=100, value=1000, key="sqft_negotiation")
        current_rent = st.number_input("Current/Proposed Monthly Rent ($)", min_value=0.0, value=5000.0)
        term_length = st.selectbox("Lease Term", ["1 year", "2 years", "3 years", "5 years", "10 years"])
    
    with col2:
        rent_per_sqft = (current_rent * 12) / square_feet if square_feet > 0 else 0
        st.metric("Rent per sqft/year", f"${rent_per_sqft:.2f}")
        security_deposit = st.number_input("Security Deposit ($)", min_value=0.0, value=current_rent * 2)
    
    if st.button("Generate Negotiation Strategy", type="primary"):
        with st.spinner("Generating AI-powered negotiation strategy..."):
            try:
                business_info = {
                    'name': business_name or 'Your Business',
                    'type': business_type,
                    'neighborhood': neighborhood or 'San Francisco',
                    'years_in_business': years_in_business
                }
                
                lease_info = {
                    'square_feet': square_feet,
                    'rent': current_rent,
                    'rent_per_sqft': rent_per_sqft,
                    'term_length': term_length,
                    'security_deposit': security_deposit
                }
                
                market_analysis = market_analyzer.analyze_neighborhood(neighborhood or "San Francisco", business_type)
                
                strategy = strategy_generator.generate_strategy(business_info, lease_info, market_analysis)
                
                st.subheader("📋 Negotiation Strategy")
                st.write(strategy['strategy'])
                
                st.subheader("🎯 Key Talking Points")
                for point in strategy['talking_points']:
                    st.write(f"• {point}")
                
                st.subheader("💡 Suggested Concessions to Request")
                for concession in strategy['concessions_to_request']:
                    st.write(f"• {concession}")
                
                st.subheader("📌 Key Points")
                for point in strategy['key_points'][:5]:
                    st.write(f"• {point}")
            
            except Exception as e:
                st.error(f"Error generating strategy: {e}")
                st.info("Note: Ensure Nemotron LLM is running and accessible.")

with tab3:
    st.header("Generate Counter-Proposal")
    
    st.subheader("Landlord's Proposal")
    col1, col2 = st.columns(2)
    
    with col1:
        landlord_rent = st.number_input("Proposed Monthly Rent ($)", min_value=0.0, value=6000.0, key="landlord_rent")
        landlord_term = st.selectbox("Proposed Term", ["1 year", "2 years", "3 years", "5 years"], key="landlord_term")
    
    with col2:
        landlord_deposit = st.number_input("Security Deposit ($)", min_value=0.0, value=landlord_rent * 2, key="landlord_deposit")
        other_terms = st.text_area("Other Terms", placeholder="Additional terms from landlord...")
    
    st.subheader("Your Business Needs")
    col3, col4 = st.columns(2)
    
    with col3:
        max_budget = st.number_input("Maximum Monthly Budget ($)", min_value=0.0, value=landlord_rent * 0.9)
        min_term = st.selectbox("Minimum Required Term", ["1 year", "2 years", "3 years"])
    
    with col4:
        must_haves = st.text_area("Must-Have Terms", placeholder="e.g., Parking, Sublease rights, etc.")
    
    if st.button("Generate Counter-Proposal", type="primary"):
        with st.spinner("Generating counter-proposal..."):
            try:
                landlord_proposal = {
                    'rent': landlord_rent,
                    'term': landlord_term,
                    'security_deposit': landlord_deposit,
                    'other_terms': other_terms
                }
                
                business_needs = {
                    'max_budget': max_budget,
                    'min_term': min_term,
                    'must_haves': must_haves
                }
                
                counter = strategy_generator.generate_counter_proposal(landlord_proposal, business_needs)
                
                st.subheader("📝 Counter-Proposal")
                st.write(counter['counter_proposal'])
                
                st.subheader("💰 Suggested Terms")
                terms = counter['suggested_terms']
                st.write(f"- **Rent Reduction:** {terms['rent_reduction']}")
                st.write(f"- **Free Rent Months:** {terms['free_rent_months']}")
                st.write(f"- **Security Deposit Reduction:** {terms['security_deposit_reduction']}")
                
                st.info("💡 Review and customize this counter-proposal before sending to your landlord.")
            
            except Exception as e:
                st.error(f"Error generating counter-proposal: {e}")
                st.info("Note: Ensure Nemotron LLM is running and accessible.")
