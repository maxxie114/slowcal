"""
Main Streamlit application for SF Business Intelligence Platform
"""

import streamlit as st
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import Config

# Page configuration
st.set_page_config(
    page_title=Config.STREAMLIT_TITLE,
    page_icon=Config.STREAMLIT_PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Main title
st.title("🏢 San Francisco Small Business Intelligence Platform")
st.markdown("---")

# Sidebar navigation
st.sidebar.title("Navigation")
st.sidebar.markdown("""
### Features
1. **Risk Dashboard** - ML-powered business failure risk prediction
2. **Lease Negotiation** - Market analysis and AI negotiation strategies
3. **City Fees** - Fee analysis and waiver opportunity finder
""")

st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.info("""
This platform helps small businesses in San Francisco:
- Predict and mitigate business failure risks
- Negotiate better lease terms
- Optimize city fees and compliance
""")

# Main content
st.markdown("""
## Welcome to the SF Small Business Intelligence Platform

This hackathon project provides three powerful features to help small businesses thrive in San Francisco:

### 🔍 Risk Prediction Engine
Use machine learning to predict business failure risk based on:
- Business age and activity
- Permit history
- Code enforcement complaints
- Location status

### 💼 Lease Negotiation Intelligence
Get AI-powered negotiation strategies with:
- Market analysis by neighborhood
- Comparable lease rates
- Customized negotiation tactics
- Counter-proposal generation

### 🏛️ City Negotiation Intelligence
Optimize your city fees and compliance:
- Fee analysis and breakdown
- Waiver opportunity identification
- Compliance requirement checklist
- Renewal schedule tracking

---

**Get Started:** Use the sidebar to navigate to each feature.
""")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>Built for SF Small Businesses | Powered by DGX Spark & Nemotron LLM</p>
</div>
""", unsafe_allow_html=True)
