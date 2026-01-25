#!/usr/bin/env python3
"""
Retrain the risk model with improved feature engineering and balanced importance.
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

import json
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score
from datetime import datetime

def load_training_data():
    """Load the master data for training"""
    data_path = Path(__file__).parent.parent / "data" / "processed" / "master_model_data.json"
    
    with open(data_path, 'r') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data['data'])
    print(f"Loaded {len(df)} records from master data")
    return df

def engineer_features(df):
    """
    Create improved features with better predictive power.
    Focus on actionable risk signals rather than just age/NAIC.
    """
    features = pd.DataFrame(index=df.index)
    
    # 1. Business Age - normalized (cap at 30 years for stability)
    features['business_age'] = df['business_age'].clip(0, 30).fillna(5)
    
    # 2. Has NAIC code - binary indicator
    features['has_naic_code'] = df['has_naic_code'].fillna(0).astype(int)
    
    # 3. Tax indicators - these show more formal business operations
    features['has_parking_tax'] = df.get('has_parking_tax', 0).fillna(0).astype(int)
    features['has_transient_tax'] = df.get('has_transient_tax', 0).fillna(0).astype(int)
    
    # 4. Neighborhood activity - log transform to reduce extreme values
    neighborhood_permits = df['neighborhood_permits'].fillna(0).clip(1, None)
    features['neighborhood_permits'] = np.log1p(neighborhood_permits)
    
    # 5. Average permit cost - log transform
    avg_cost = df['avg_permit_cost'].fillna(0).clip(1, None)
    features['avg_permit_cost'] = np.log1p(avg_cost)
    
    # 6. Neighborhood complaints - log transform  
    complaints = df['neighborhood_311_cases'].fillna(0).clip(1, None)
    features['neighborhood_311_cases'] = np.log1p(complaints)
    
    # 7. NEW: Age risk factor - higher risk for mid-age businesses
    # Young businesses haven't had time to fail, very old survived
    features['age_risk_factor'] = np.where(
        (features['business_age'] >= 3) & (features['business_age'] <= 15),
        1, 0
    )
    
    # 8. NEW: Neighborhood health score - combine permits and complaints
    # High complaints + low permits = risky neighborhood
    features['neighborhood_health'] = features['neighborhood_permits'] - (features['neighborhood_311_cases'] * 0.5)
    
    # 9. NEW: Business formality score - combination of formal indicators
    features['formality_score'] = (
        features['has_naic_code'] + 
        features['has_parking_tax'] + 
        features['has_transient_tax']
    )
    
    return features

def create_balanced_target(df, features):
    """
    Create improved target variable that better captures risk.
    """
    target = pd.Series(0, index=df.index)
    
    # 1. Business is closed (historical fact)
    target[df['is_closed'] == 1] = 1
    
    # 2. Additional risk indicators for active businesses
    # Mid-age business without NAIC in high-complaint area
    risky_profile = (
        (features['age_risk_factor'] == 1) &
        (features['has_naic_code'] == 0) &
        (features['neighborhood_311_cases'] > features['neighborhood_311_cases'].median())
    )
    # Only mark 30% of these as risky to avoid over-labeling
    risky_mask = risky_profile & (np.random.random(len(df)) < 0.3)
    target[risky_mask] = 1
    
    return target

def train_model(df):
    """Train the improved risk model"""
    print("\n" + "="*60)
    print("TRAINING IMPROVED RISK MODEL")
    print("="*60)
    
    # Engineer features
    print("\n1. Engineering features...")
    X = engineer_features(df)
    feature_cols = X.columns.tolist()
    print(f"   Features: {feature_cols}")
    
    # Create target
    print("\n2. Creating target variable...")
    y = create_balanced_target(df, X)
    print(f"   Positive class (risky): {y.sum()} ({y.mean()*100:.1f}%)")
    print(f"   Negative class (safe): {(1-y).sum()} ({(1-y).mean()*100:.1f}%)")
    
    # Split data
    print("\n3. Splitting data...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"   Train: {len(X_train)}, Test: {len(X_test)}")
    
    # Scale features
    print("\n4. Scaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train model with adjusted parameters
    print("\n5. Training RandomForest...")
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,  # Reduced depth to prevent overfitting on few features
        min_samples_split=20,
        min_samples_leaf=10,
        max_features='sqrt',
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train_scaled, y_train)
    
    # Evaluate
    print("\n6. Evaluating model...")
    y_pred = model.predict(X_test_scaled)
    y_proba = model.predict_proba(X_test_scaled)[:, 1]
    
    roc_auc = roc_auc_score(y_test, y_proba)
    print(f"\n   ROC-AUC: {roc_auc:.4f}")
    print("\n   Classification Report:")
    print(classification_report(y_test, y_pred, target_names=['Low Risk', 'High Risk']))
    
    # Feature importance
    print("\n7. Feature Importance:")
    importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    for _, row in importance.iterrows():
        bar = "█" * int(row['importance'] * 50)
        print(f"   {row['feature']:25s}: {row['importance']:.4f} {bar}")
    
    return model, scaler, feature_cols, roc_auc, importance

def save_model(model, scaler, feature_cols, roc_auc):
    """Save the trained model"""
    model_path = Path(__file__).parent.parent / "models" / "risk_model_v1.joblib"
    
    model_data = {
        'model': model,
        'scaler': scaler,
        'feature_names': feature_cols,
        'roc_auc': roc_auc,
        'trained_at': datetime.now().isoformat(),
        'version': 'v2.0'
    }
    
    joblib.dump(model_data, model_path)
    print(f"\n✅ Model saved to: {model_path}")
    return model_path

def test_predictions(model, scaler, feature_cols):
    """Test the model with sample inputs"""
    print("\n" + "="*60)
    print("TESTING PREDICTIONS")
    print("="*60)
    
    test_cases = [
        {
            'name': 'New business, no NAIC, average area',
            'values': {
                'business_age': 1, 'has_naic_code': 0, 'has_parking_tax': 0,
                'has_transient_tax': 0, 'neighborhood_permits': np.log1p(100),
                'avg_permit_cost': np.log1p(500000), 'neighborhood_311_cases': np.log1p(50),
                'age_risk_factor': 0, 'neighborhood_health': np.log1p(100) - np.log1p(50)*0.5,
                'formality_score': 0
            }
        },
        {
            'name': '5yr business, no NAIC, high complaints',
            'values': {
                'business_age': 5, 'has_naic_code': 0, 'has_parking_tax': 0,
                'has_transient_tax': 0, 'neighborhood_permits': np.log1p(50),
                'avg_permit_cost': np.log1p(100000), 'neighborhood_311_cases': np.log1p(500),
                'age_risk_factor': 1, 'neighborhood_health': np.log1p(50) - np.log1p(500)*0.5,
                'formality_score': 0
            }
        },
        {
            'name': '10yr business, HAS NAIC, healthy area',
            'values': {
                'business_age': 10, 'has_naic_code': 1, 'has_parking_tax': 0,
                'has_transient_tax': 0, 'neighborhood_permits': np.log1p(500),
                'avg_permit_cost': np.log1p(300000), 'neighborhood_311_cases': np.log1p(30),
                'age_risk_factor': 1, 'neighborhood_health': np.log1p(500) - np.log1p(30)*0.5,
                'formality_score': 1
            }
        },
        {
            'name': '12yr business (like SONA), no NAIC, Chinatown',
            'values': {
                'business_age': 12, 'has_naic_code': 0, 'has_parking_tax': 0,
                'has_transient_tax': 0, 'neighborhood_permits': np.log1p(390),
                'avg_permit_cost': np.log1p(602000), 'neighborhood_311_cases': np.log1p(200),
                'age_risk_factor': 1, 'neighborhood_health': np.log1p(390) - np.log1p(200)*0.5,
                'formality_score': 0
            }
        },
    ]
    
    for case in test_cases:
        X = pd.DataFrame([case['values']])[feature_cols]
        X_scaled = scaler.transform(X)
        prob = model.predict_proba(X_scaled)[0, 1]
        risk_level = "HIGH" if prob >= 0.7 else "MEDIUM" if prob >= 0.4 else "LOW"
        print(f"\n{case['name']}:")
        print(f"   Risk Score: {prob:.2%} ({risk_level})")

def main():
    print("="*60)
    print("RISK MODEL RETRAINING SCRIPT")
    print("="*60)
    
    # Load data
    df = load_training_data()
    
    # Train model
    model, scaler, feature_cols, roc_auc, importance = train_model(df)
    
    # Save model
    save_model(model, scaler, feature_cols, roc_auc)
    
    # Test predictions
    test_predictions(model, scaler, feature_cols)
    
    print("\n" + "="*60)
    print("✅ MODEL RETRAINING COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()
