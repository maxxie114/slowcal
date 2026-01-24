"""
City Fees and Compliance Intelligence Page
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.city_intelligence.fee_analysis import FeeAnalyzer
from src.city_intelligence.compliance_advisor import ComplianceAdvisor
from src.utils.nemotron_client import NemotronClient
from src.utils.config import Config

st.set_page_config(
    page_title="City Fees",
    page_icon="🏛️",
    layout="wide"
)

st.title("🏛️ City Fees & Compliance Intelligence")
st.markdown("Analyze fees, find waiver opportunities, and ensure compliance")

# Initialize components
fee_analyzer = FeeAnalyzer()
nemotron_client = NemotronClient()
compliance_advisor = ComplianceAdvisor(nemotron_client)

# Tabs
tab1, tab2, tab3 = st.tabs(["Fee Analysis", "Compliance Requirements", "Renewal Schedule"])

with tab1:
    st.header("Fee Analysis & Waiver Opportunities")
    
    st.subheader("Business Information")
    col1, col2 = st.columns(2)
    
    with col1:
        business_type = st.selectbox(
            "Business Type",
            ["Retail", "Restaurant", "Office", "Manufacturing", "Nonprofit", "Other"]
        )
        annual_revenue = st.number_input("Annual Revenue ($)", min_value=0, value=100000, step=10000)
        years_in_business = st.number_input("Years in Business", min_value=0, max_value=50, value=5)
    
    with col2:
        is_nonprofit = st.checkbox("Registered Nonprofit (501c3)")
        location = st.text_input("Business Location", placeholder="e.g., Mission District")
    
    st.subheader("Required Permits & Licenses")
    st.write("Select all permits/licenses your business needs:")
    
    permit_options = [
        "Business Registration",
        "Business License Renewal",
        "Building Permit",
        "Planning Review",
        "Health Permit",
        "Fire Inspection",
        "Sign Permit",
        "Parking Permit"
    ]
    
    selected_permits = st.multiselect(
        "Select Permits",
        permit_options,
        default=["Business Registration", "Business License Renewal"]
    )
    
    if st.button("Analyze Fees", type="primary"):
        with st.spinner("Analyzing fees and waiver opportunities..."):
            try:
                business_info = {
                    'annual_revenue': annual_revenue,
                    'years_in_business': years_in_business,
                    'is_nonprofit': is_nonprofit,
                    'business_type': business_type
                }
                
                analysis = fee_analyzer.analyze_fees(business_type, selected_permits, business_info)
                
                # Display results
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Fees", f"${analysis['total_fees']:,.2f}")
                col2.metric("Waiver Savings", f"${analysis['waiver_savings']:,.2f}")
                col3.metric("Final Fees", f"${analysis['final_fees_after_waivers']:,.2f}", 
                           delta=f"-${analysis['waiver_savings']:,.2f}")
                
                st.subheader("Fee Breakdown")
                fee_df = pd.DataFrame(list(analysis['fee_breakdown'].items()), 
                                     columns=['Permit/License', 'Fee ($)'])
                st.dataframe(fee_df, use_container_width=True)
                
                st.subheader("Waiver Opportunities")
                for waiver in analysis['waiver_opportunities']:
                    if waiver.get('eligible', False):
                        with st.expander(f"✅ {waiver['type']} - Eligible"):
                            st.write(f"**Description:** {waiver['description']}")
                            st.write(f"**Discount:** {waiver['discount']*100:.0f}%")
                            st.write(f"**Action Required:** {waiver.get('action_required', 'Submit application')}")
                    else:
                        st.info(f"❌ {waiver['type']} - {waiver['description']}")
                
                st.subheader("Recommendations")
                for rec in analysis['recommendations']:
                    st.write(f"• {rec}")
                
                # Timeline
                st.subheader("Estimated Processing Timeline")
                timeline = fee_analyzer.get_fee_timeline(selected_permits)
                st.write(f"**Estimated Total Time:** {timeline['estimated_total_weeks']:.1f} weeks ({timeline['estimated_total_days']} business days)")
                st.info(f"💡 {timeline['recommendation']}")
            
            except Exception as e:
                st.error(f"Error analyzing fees: {e}")

with tab2:
    st.header("Compliance Requirements")
    
    st.subheader("Business Details")
    col1, col2 = st.columns(2)
    
    with col1:
        comp_business_type = st.selectbox(
            "Business Type",
            ["Retail", "Restaurant", "Office", "Manufacturing", "Service", "Other"],
            key="comp_business_type"
        )
        comp_location = st.text_input("Location/Neighborhood", placeholder="e.g., Mission District", key="comp_location")
        square_feet = st.number_input("Square Footage", min_value=0, value=1000, key="comp_sqft")
    
    with col2:
        num_employees = st.number_input("Number of Employees", min_value=0, value=5, key="comp_employees")
        serves_food = st.checkbox("Serves Food", key="comp_food")
        serves_alcohol = st.checkbox("Serves Alcohol", key="comp_alcohol")
        has_physical_location = st.checkbox("Has Physical Location", value=True, key="comp_location_check")
        requires_construction = st.checkbox("Requires Construction/Renovation", key="comp_construction")
    
    if st.button("Get Compliance Requirements", type="primary"):
        with st.spinner("Generating compliance requirements..."):
            try:
                business_info = {
                    'square_feet': square_feet,
                    'num_employees': num_employees,
                    'serves_food': serves_food,
                    'serves_alcohol': serves_alcohol,
                    'has_physical_location': has_physical_location,
                    'requires_construction': requires_construction,
                    'has_employees': num_employees > 0
                }
                
                requirements = compliance_advisor.get_compliance_requirements(
                    comp_business_type,
                    comp_location or "San Francisco",
                    business_info
                )
                
                st.subheader("📋 Compliance Requirements")
                st.write(requirements['requirements'])
                
                st.subheader("✅ Priority Items")
                for item in requirements['priority_items']:
                    st.write(f"• {item}")
                
                st.subheader("📝 Checklist")
                for item in requirements['checklist'][:15]:
                    st.checkbox(item, key=f"check_{hash(item)}")
            
            except Exception as e:
                st.error(f"Error getting requirements: {e}")
                st.info("Note: Ensure Nemotron LLM is running and accessible.")
    
    # Compliance Status Check
    st.subheader("Check Current Compliance Status")
    current_permits = st.multiselect(
        "Current Permits/Licenses",
        [
            "Business Registration Certificate",
            "Business Tax Certificate",
            "Certificate of Occupancy",
            "Health Department Permit",
            "ABC License",
            "Building Permits",
            "Planning Department Approval",
            "Workers' Compensation Insurance",
            "Payroll Tax Registration"
        ]
    )
    
    if st.button("Check Compliance Status"):
        business_info = {
            'business_type': comp_business_type,
            'has_employees': num_employees > 0,
            'serves_food': serves_food,
            'serves_alcohol': serves_alcohol,
            'requires_construction': requires_construction
        }
        
        status = compliance_advisor.check_compliance_status(business_info, current_permits)
        
        col1, col2 = st.columns(2)
        col1.metric("Compliance Score", f"{status['compliance_score']:.0f}%")
        col2.metric("Missing Items", len(status['missing_items']))
        
        if status['is_compliant']:
            st.success("✅ Your business is compliant!")
        else:
            st.warning(f"⚠️ {len(status['missing_items'])} compliance item(s) missing")
            st.write("**Missing Items:**")
            for item in status['missing_items']:
                st.write(f"• {item}")
        
        st.subheader("Recommendations")
        for rec in status['recommendations']:
            st.write(f"• {rec}")

with tab3:
    st.header("Permit Renewal Schedule")
    
    current_permits_renewal = st.multiselect(
        "Your Current Permits/Licenses",
        [
            "Business Registration Certificate",
            "Business Tax Certificate",
            "Health Department Permit",
            "ABC License",
            "Certificate of Occupancy",
            "Building Permits"
        ],
        key="renewal_permits"
    )
    
    if st.button("Get Renewal Schedule"):
        schedule = compliance_advisor.get_renewal_schedule(current_permits_renewal)
        
        st.subheader("Renewal Schedule")
        for permit, period in schedule['renewal_schedule'].items():
            st.write(f"• **{permit}:** {period}")
        
        if schedule['annual_renewals']:
            st.subheader("Annual Renewals Required")
            for permit in schedule['annual_renewals']:
                st.write(f"• {permit}")
        
        st.info(f"💡 {schedule['recommendation']}")
