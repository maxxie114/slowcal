"""
Merge multiple datasets for analysis
"""

import pandas as pd
from pathlib import Path
from ..utils.config import Config
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
    Merge business registry with permits and complaints data
    
    Args:
        business_df: Business registry DataFrame
        permits_df: Optional permits DataFrame
        complaints_df: Optional complaints DataFrame
        merge_key: Column name to merge on
    
    Returns:
        Merged DataFrame
    """
    merged = business_df.copy()
    
    # Merge permits
    if permits_df is not None and not permits_df.empty:
        if merge_key in permits_df.columns:
            # Aggregate permits per business
            permits_agg = permits_df.groupby(merge_key).agg({
                'permit_type': 'count',
                'estimated_cost': ['sum', 'mean'],
                'filed_date': ['min', 'max']
            }).reset_index()
            
            # Flatten column names
            permits_agg.columns = [f"{col[0]}_{col[1]}" if col[1] else col[0] 
                                  for col in permits_agg.columns]
            permits_agg = permits_agg.rename(columns={
                f"{merge_key}_": merge_key,
                'permit_type_count': 'total_permits',
                'estimated_cost_sum': 'total_permit_cost',
                'estimated_cost_mean': 'avg_permit_cost'
            })
            
            merged = merged.merge(permits_agg, on=merge_key, how='left')
            merged['total_permits'] = merged['total_permits'].fillna(0)
            logger.info("Merged permits data")
    
    # Merge complaints
    if complaints_df is not None and not complaints_df.empty:
        if merge_key in complaints_df.columns:
            # Aggregate complaints per business
            complaints_agg = complaints_df.groupby(merge_key).agg({
                'opened_date': 'count',
                'is_closed': 'sum'
            }).reset_index()
            
            complaints_agg = complaints_agg.rename(columns={
                'opened_date': 'total_complaints',
                'is_closed': 'closed_complaints'
            })
            
            merged = merged.merge(complaints_agg, on=merge_key, how='left')
            merged['total_complaints'] = merged['total_complaints'].fillna(0)
            merged['closed_complaints'] = merged['closed_complaints'].fillna(0)
            merged['open_complaints'] = merged['total_complaints'] - merged['closed_complaints']
            logger.info("Merged complaints data")
    
    # Create risk features
    merged['has_permits'] = merged.get('total_permits', 0) > 0
    merged['has_complaints'] = merged.get('total_complaints', 0) > 0
    merged['complaint_rate'] = merged.get('total_complaints', 0) / (merged.get('total_permits', 0) + 1)
    
    logger.info(f"Merged dataset: {len(merged)} records")
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
