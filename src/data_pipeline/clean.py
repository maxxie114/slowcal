"""
Clean and preprocess SF.gov business data
"""

import pandas as pd
import numpy as np
from pathlib import Path
from ..utils.config import Config
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def clean_business_data(df: pd.DataFrame, dataset_type: str = "business") -> pd.DataFrame:
    """
    Clean business data based on dataset type
    
    Args:
        df: Raw DataFrame
        dataset_type: Type of dataset ('business', 'permits', 'complaints')
    
    Returns:
        Cleaned DataFrame
    """
    df = df.copy()
    
    if dataset_type == "business":
        return _clean_business_registry(df)
    elif dataset_type == "permits":
        return _clean_permits(df)
    elif dataset_type == "complaints":
        return _clean_complaints(df)
    else:
        logger.warning(f"Unknown dataset type: {dataset_type}, returning original")
        return df

def _clean_business_registry(df: pd.DataFrame) -> pd.DataFrame:
    """Clean business registry data"""
    # Standardize column names
    if 'dba_name' in df.columns:
        df['business_name'] = df['dba_name'].fillna(df.get('business_name', ''))
    
    # Parse dates
    date_columns = ['location_start_date', 'location_end_date', 'business_start_date']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Extract year from business start date
    if 'business_start_date' in df.columns:
        df['business_start_year'] = df['business_start_date'].dt.year
    
    # Clean location data
    if 'location' in df.columns:
        df['has_location'] = df['location'].notna()
    
    # Clean NAICS codes
    if 'naics_code' in df.columns:
        df['naics_code'] = df['naics_code'].astype(str).str.replace(r'[^0-9]', '', regex=True)
        df['naics_code'] = df['naics_code'].replace('', np.nan)
    
    # Create active status flag
    if 'location_end_date' in df.columns:
        df['is_active'] = df['location_end_date'].isna()
    
    logger.info(f"Cleaned business registry: {len(df)} records")
    return df

def _clean_permits(df: pd.DataFrame) -> pd.DataFrame:
    """Clean building permits data"""
    # Parse dates
    date_columns = ['filed_date', 'issued_date', 'completed_date']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Extract year
    if 'filed_date' in df.columns:
        df['permit_year'] = df['filed_date'].dt.year
    
    # Clean permit type
    if 'permit_type' in df.columns:
        df['permit_type'] = df['permit_type'].astype(str).str.strip()
    
    # Clean cost data
    cost_columns = ['estimated_cost', 'revised_cost', 'existing_cost']
    for col in cost_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    logger.info(f"Cleaned permits: {len(df)} records")
    return df

def _clean_complaints(df: pd.DataFrame) -> pd.DataFrame:
    """Clean code enforcement complaints data"""
    # Parse dates
    date_columns = ['opened_date', 'closed_date']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Extract year
    if 'opened_date' in df.columns:
        df['complaint_year'] = df['opened_date'].dt.year
    
    # Create status flag
    if 'closed_date' in df.columns:
        df['is_closed'] = df['closed_date'].notna()
    
    logger.info(f"Cleaned complaints: {len(df)} records")
    return df

def save_cleaned_data(df: pd.DataFrame, filename: str, output_dir: Optional[Path] = None):
    """Save cleaned data to processed directory"""
    output_dir = output_dir or Config.PROCESSED_DATA_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / filename
    df.to_parquet(output_path, index=False)
    logger.info(f"Saved cleaned data to {output_path}")
