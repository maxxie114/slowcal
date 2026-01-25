"""
Clean and preprocess SF.gov business data
"""

import pandas as pd
import numpy as np
from pathlib import Path
from utils.config import Config
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
        df['business_name'] = df['dba_name'].fillna(df.get('ownership_name', ''))
    
    # Parse dates - use actual column names from SF Open Data
    date_columns = ['location_start_date', 'location_end_date', 'dba_start_date', 'dba_end_date']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Extract year from dba_start_date (business start date)
    if 'dba_start_date' in df.columns:
        df['business_start_year'] = df['dba_start_date'].dt.year
    elif 'location_start_date' in df.columns:
        df['business_start_year'] = df['location_start_date'].dt.year
    
    # Clean location data
    if 'location' in df.columns:
        df['has_location'] = df['location'].notna()
    else:
        # Check for address fields
        df['has_location'] = df.get('full_business_address', pd.Series()).notna()
    
    # Create active status flag based on location_end_date or dba_end_date
    if 'location_end_date' in df.columns:
        df['is_active'] = df['location_end_date'].isna()
    elif 'dba_end_date' in df.columns:
        df['is_active'] = df['dba_end_date'].isna()
    
    # Use certificate_number as business account number if available
    if 'certificate_number' in df.columns:
        df['business_account_number'] = df['certificate_number']

    logger.info(f"Cleaned business registry: {len(df)} records")
    return df

def _clean_permits(df: pd.DataFrame) -> pd.DataFrame:
    """Clean building permits data"""
    # Parse dates - use actual column names from SF Open Data
    date_columns = ['filed_date', 'issued_date', 'approved_date', 'permit_creation_date', 'status_date']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Extract year from filed_date or permit_creation_date
    if 'filed_date' in df.columns:
        df['permit_year'] = df['filed_date'].dt.year
    elif 'permit_creation_date' in df.columns:
        df['permit_year'] = df['permit_creation_date'].dt.year
    
    # Clean permit type
    if 'permit_type' in df.columns:
        df['permit_type'] = df['permit_type'].astype(str).str.strip()
    
    # Clean cost data
    cost_columns = ['estimated_cost', 'revised_cost']
    for col in cost_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    logger.info(f"Cleaned permits: {len(df)} records")
    return df

def _clean_complaints(df: pd.DataFrame) -> pd.DataFrame:
    """Clean 311 cases / code enforcement complaints data"""
    # Parse dates - use actual column names from SF 311 Cases dataset
    date_columns = ['requested_datetime', 'closed_date', 'updated_datetime']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Create opened_date alias for compatibility
    if 'requested_datetime' in df.columns:
        df['opened_date'] = df['requested_datetime']
    
    # Extract year
    if 'opened_date' in df.columns:
        df['complaint_year'] = df['opened_date'].dt.year
    elif 'requested_datetime' in df.columns:
        df['complaint_year'] = df['requested_datetime'].dt.year
    
    # Create status flag based on closed_date or status_description
    if 'closed_date' in df.columns:
        df['is_closed'] = df['closed_date'].notna()
    elif 'status_description' in df.columns:
        df['is_closed'] = df['status_description'].str.lower() == 'closed'
    
    logger.info(f"Cleaned complaints: {len(df)} records")
    return df
    
    logger.info(f"Cleaned complaints: {len(df)} records")
    return df

def save_cleaned_data(df: pd.DataFrame, filename: str, output_dir: Optional[Path] = None):
    """Save cleaned data to processed directory"""
    output_dir = output_dir or Config.PROCESSED_DATA_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / filename
    df.to_parquet(output_path, index=False)
    logger.info(f"Saved cleaned data to {output_path}")
