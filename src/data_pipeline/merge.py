"""
Merge multiple datasets for analysis
"""

import pandas as pd
from pathlib import Path
from utils.config import Config
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

def merge_datasets(
    business_df: pd.DataFrame,
    permits_df: Optional[pd.DataFrame] = None,
    complaints_df: Optional[pd.DataFrame] = None,
    merge_key: str = "business_account_number"
) -> pd.DataFrame:
    """
    Merge business registry with permits and complaints data.
    
    Since datasets may not share a common key, this function:
    1. Tries to merge on merge_key if available
    2. Falls back to address-based matching
    3. If no match possible, adds aggregate statistics as constants
    
    Args:
        business_df: Business registry DataFrame
        permits_df: Optional permits DataFrame
        complaints_df: Optional complaints DataFrame
        merge_key: Column name to merge on
    
    Returns:
        Merged DataFrame with risk features
    """
    merged = business_df.copy()
    
    # Initialize columns that downstream code expects
    merged['total_permits'] = 0
    merged['total_permit_cost'] = 0.0
    merged['avg_permit_cost'] = 0.0
    merged['total_complaints'] = 0
    merged['closed_complaints'] = 0
    merged['open_complaints'] = 0
    
    # Try to merge permits
    if permits_df is not None and not permits_df.empty:
        if merge_key in permits_df.columns and merge_key in merged.columns:
            # Direct merge on business key
            permits_agg = permits_df.groupby(merge_key).agg({
                'permit_type': 'count',
                'estimated_cost': ['sum', 'mean'],
            }).reset_index()
            permits_agg.columns = [merge_key, 'total_permits', 'total_permit_cost', 'avg_permit_cost']
            
            merged = merged.merge(permits_agg, on=merge_key, how='left', suffixes=('', '_permit'))
            merged['total_permits'] = merged['total_permits'].fillna(0)
            merged['total_permit_cost'] = merged['total_permit_cost'].fillna(0)
            merged['avg_permit_cost'] = merged['avg_permit_cost'].fillna(0)
            logger.info("Merged permits data on business key")
        else:
            # No common key - add permit statistics at neighborhood/zip level or as summary
            logger.warning(f"No common key '{merge_key}' for permits merge. Adding summary stats.")
            # Add neighborhood-level permit density if possible
            if 'business_zip' in merged.columns and 'zipcode' in permits_df.columns:
                zip_permits = permits_df.groupby('zipcode').size().reset_index(name='zip_permit_count')
                merged = merged.merge(zip_permits, left_on='business_zip', right_on='zipcode', how='left')
                merged['total_permits'] = merged['zip_permit_count'].fillna(0)
                merged.drop(columns=['zipcode', 'zip_permit_count'], errors='ignore', inplace=True)
                logger.info("Merged permits by zipcode")
    
    # Try to merge complaints
    if complaints_df is not None and not complaints_df.empty:
        if merge_key in complaints_df.columns and merge_key in merged.columns:
            # Direct merge on business key
            complaints_agg = complaints_df.groupby(merge_key).agg({
                'opened_date': 'count',
                'is_closed': 'sum'
            }).reset_index()
            complaints_agg.columns = [merge_key, 'total_complaints', 'closed_complaints']
            
            merged = merged.merge(complaints_agg, on=merge_key, how='left', suffixes=('', '_complaint'))
            merged['total_complaints'] = merged['total_complaints'].fillna(0)
            merged['closed_complaints'] = merged['closed_complaints'].fillna(0)
            merged['open_complaints'] = merged['total_complaints'] - merged['closed_complaints']
            logger.info("Merged complaints data on business key")
        else:
            # No common key - try address or neighborhood matching
            logger.warning(f"No common key '{merge_key}' for complaints merge. Adding summary stats.")
            if 'business_zip' in merged.columns and 'zipcode' in complaints_df.columns:
                zip_complaints = complaints_df.groupby('zipcode').agg({
                    'service_request_id': 'count',
                    'is_closed': 'sum'
                }).reset_index()
                zip_complaints.columns = ['zipcode', 'zip_complaints', 'zip_closed']
                merged = merged.merge(zip_complaints, left_on='business_zip', right_on='zipcode', how='left')
                merged['total_complaints'] = merged['zip_complaints'].fillna(0)
                merged['closed_complaints'] = merged['zip_closed'].fillna(0)
                merged['open_complaints'] = merged['total_complaints'] - merged['closed_complaints']
                merged.drop(columns=['zipcode', 'zip_complaints', 'zip_closed'], errors='ignore', inplace=True)
                logger.info("Merged complaints by zipcode")
            elif 'neighborhoods_sffind_boundaries' in complaints_df.columns:
                # Use neighborhood-level stats
                neighborhood_complaints = complaints_df.groupby('neighborhoods_sffind_boundaries').agg({
                    'service_request_id': 'count',
                    'is_closed': 'sum'
                }).reset_index()
                neighborhood_complaints.columns = ['neighborhood', 'total_complaints', 'closed_complaints']
                # Store as reference data
                logger.info(f"Complaints by neighborhood available: {len(neighborhood_complaints)} neighborhoods")
    
    # Create risk features
    merged['has_permits'] = merged['total_permits'] > 0
    merged['has_complaints'] = merged['total_complaints'] > 0
    merged['complaint_rate'] = merged['total_complaints'] / (merged['total_permits'] + 1)
    
    logger.info(f"Merged dataset: {len(merged)} records with columns: {list(merged.columns)}")
    return merged

def load_processed_data(filename: str, data_dir: Optional[Path] = None) -> pd.DataFrame:
    """Load processed data from parquet file"""
    data_dir = data_dir or Config.PROCESSED_DATA_DIR
    file_path = data_dir / filename
    
    if file_path.exists():
        return pd.read_parquet(file_path)
    else:
        logger.warning(f"File not found: {file_path}")
        return pd.DataFrame()
