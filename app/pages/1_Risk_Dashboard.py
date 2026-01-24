"""
Risk Prediction Dashboard
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.risk_engine.model import RiskPredictor
from src.risk_engine.alerts import RiskAlertSystem
from src.data_pipeline.download import download_business_registry
from src.data_pipeline.clean import clean_business_data
from src.utils.config import Config

st.set_page_config(
    page_title="Risk Dashboard",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Risk Prediction Dashboard")
st.markdown("Predict business failure risk using ML models trained on SF business data")

# Initialize session state
if 'risk_predictor' not in st.session_state:
    st.session_state.risk_predictor = None
if 'predictions' not in st.session_state:
    st.session_state.predictions = None

# Sidebar for model training
with st.sidebar:
    st.header("Model Training")
    
    if st.button("Train Risk Model", type="primary"):
        with st.spinner("Training model... This may take a few minutes."):
            try:
                # Download and prepare data
                st.info("Downloading business data...")
                business_df = download_business_registry()
                
                st.info("Cleaning data...")
                business_df = clean_business_data(business_df, dataset_type="business")
                
                # Train model
                st.info("Training ML model...")
                predictor = RiskPredictor(model_type="random_forest")
                metrics = predictor.train(business_df)
                
                # Save model
                predictor.save()
                st.session_state.risk_predictor = predictor
                
                st.success("Model trained successfully!")
                st.json(metrics)
            
            except Exception as e:
                st.error(f"Error training model: {e}")
    
    # Load existing model
    if st.button("Load Existing Model"):
        try:
            model_path = Config.MODELS_DIR / f"risk_model_{Config.RISK_MODEL_VERSION}.joblib"
            if model_path.exists():
                predictor = RiskPredictor.load(model_path)
                st.session_state.risk_predictor = predictor
                st.success("Model loaded successfully!")
            else:
                st.warning("No saved model found. Please train a model first.")
        except Exception as e:
            st.error(f"Error loading model: {e}")

# Main content
if st.session_state.risk_predictor is None:
    st.warning("⚠️ Please train or load a model from the sidebar to get started.")
    
    st.markdown("""
    ### How it works:
    1. Click "Train Risk Model" to download SF business data and train the ML model
    2. Or click "Load Existing Model" if you've trained one before
    3. Once loaded, you can analyze individual businesses or view risk trends
    """)
else:
    st.success("✅ Model loaded and ready!")
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["Business Analysis", "Risk Trends", "Alerts"])
    
    with tab1:
        st.header("Analyze Individual Business")
        
        col1, col2 = st.columns(2)
        
        with col1:
            business_name = st.text_input("Business Name", placeholder="Enter business name")
            business_account = st.text_input("Business Account Number (optional)")
        
        with col2:
            business_age = st.number_input("Years in Business", min_value=0, max_value=50, value=5)
            has_active_location = st.checkbox("Has Active Location", value=True)
        
        col3, col4 = st.columns(2)
        
        with col3:
            total_permits = st.number_input("Total Permits", min_value=0, value=0)
            total_complaints = st.number_input("Total Complaints", min_value=0, value=0)
        
        with col4:
            open_complaints = st.number_input("Open Complaints", min_value=0, value=0)
            total_permit_cost = st.number_input("Total Permit Cost ($)", min_value=0.0, value=0.0)
        
        if st.button("Predict Risk", type="primary"):
            # Create sample business data
            business_data = pd.DataFrame([{
                'business_name': business_name or 'Sample Business',
                'business_account_number': business_account or '12345',
                'business_start_year': 2024 - business_age,
                'is_active': has_active_location,
                'has_location': has_active_location,
                'total_permits': total_permits,
                'total_complaints': total_complaints,
                'open_complaints': open_complaints,
                'total_permit_cost': total_permit_cost,
                'avg_permit_cost': total_permit_cost / max(total_permits, 1),
                'has_permits': total_permits > 0,
                'has_complaints': total_complaints > 0,
                'complaint_rate': total_complaints / max(total_permits, 1)
            }])
            
            # Predict
            predictions = st.session_state.risk_predictor.predict(business_data)
            st.session_state.predictions = predictions
            
            # Display results
            risk_score = predictions.iloc[0]['risk_score']
            risk_level = predictions.iloc[0]['risk_level']
            
            # Risk gauge
            fig = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = risk_score * 100,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Risk Score (%)"},
                delta = {'reference': 50},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 40], 'color': "lightgreen"},
                        {'range': [40, 70], 'color': "yellow"},
                        {'range': [70, 100], 'color': "red"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 70
                    }
                }
            ))
            
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
            
            # Risk level badge
            if risk_level == 'High':
                st.error(f"⚠️ **HIGH RISK** - Risk Score: {risk_score:.2%}")
            elif risk_level == 'Medium':
                st.warning(f"⚡ **MEDIUM RISK** - Risk Score: {risk_score:.2%}")
            else:
                st.success(f"✅ **LOW RISK** - Risk Score: {risk_score:.2%}")
            
            # Feature importance
            st.subheader("Key Risk Factors")
            feature_importance = st.session_state.risk_predictor.get_feature_importance()
            top_features = feature_importance.head(5)
            
            fig2 = px.bar(
                top_features,
                x='importance',
                y='feature',
                orientation='h',
                title="Top Risk Factors",
                labels={'importance': 'Importance', 'feature': 'Factor'}
            )
            st.plotly_chart(fig2, use_container_width=True)
    
    with tab2:
        st.header("Risk Trends Analysis")
        
        if st.button("Analyze All Businesses"):
            with st.spinner("Analyzing business data..."):
                try:
                    # Download and analyze
                    business_df = download_business_registry()
                    business_df = clean_business_data(business_df, dataset_type="business")
                    
                    # Sample for performance (if too large)
                    if len(business_df) > 1000:
                        business_df = business_df.sample(1000, random_state=42)
                    
                    # Predict
                    predictions = st.session_state.risk_predictor.predict(business_df)
                    st.session_state.predictions = predictions
                    
                    # Visualizations
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Risk distribution
                        fig = px.histogram(
                            predictions,
                            x='risk_score',
                            nbins=30,
                            title="Risk Score Distribution",
                            labels={'risk_score': 'Risk Score', 'count': 'Number of Businesses'}
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        # Risk by level
                        risk_counts = predictions['risk_level'].value_counts()
                        fig = px.pie(
                            values=risk_counts.values,
                            names=risk_counts.index,
                            title="Businesses by Risk Level"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Risk by business age
                    if 'business_start_year' in predictions.columns:
                        predictions['business_age'] = 2024 - predictions['business_start_year']
                        fig = px.scatter(
                            predictions,
                            x='business_age',
                            y='risk_score',
                            color='risk_level',
                            title="Risk Score vs Business Age",
                            labels={'business_age': 'Business Age (years)', 'risk_score': 'Risk Score'}
                        )
                        st.plotly_chart(fig, use_container_width=True)
                
                except Exception as e:
                    st.error(f"Error analyzing businesses: {e}")
    
    with tab3:
        st.header("Risk Alerts")
        
        if st.session_state.predictions is not None:
            alert_system = RiskAlertSystem()
            alerts = alert_system.generate_alerts(st.session_state.predictions)
            
            summary = alert_system.get_alerts_summary()
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Alerts", summary['total_alerts'])
            col2.metric("High Risk", summary['high_risk'], delta=None)
            col3.metric("Medium Risk", summary['medium_risk'], delta=None)
            
            if alerts:
                st.subheader("Alert Details")
                for alert in alerts[:20]:  # Show top 20
                    with st.expander(f"{alert['risk_level']} Risk: {alert['business_name']} (Score: {alert['risk_score']:.2%})"):
                        st.write(f"**Message:** {alert['message']}")
                        st.write("**Recommendations:**")
                        for rec in alert['recommendations']:
                            st.write(f"- {rec}")
            else:
                st.info("No alerts generated. All businesses appear to be low risk.")
        else:
            st.info("Run a prediction first to generate alerts.")
