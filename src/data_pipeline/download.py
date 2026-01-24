"""
Download data from SF.gov Open Data API
"""

import requests
import pandas as pd
import json
from pathlib import Path
from ..utils.config import Config
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def download_sf_data(dataset_id: str, output_path: Optional[Path] = None, limit: int = 50000) -> pd.DataFrame:
    """
    Download data from SF.gov Open Data API
    
    Args:
        dataset_id: Dataset identifier (e.g., 'rqzj-sfat' for business registry)
        output_path: Optional path to save raw data JSON
        limit: Maximum number of records to download
    
    Returns:
        DataFrame with downloaded data
    """
    url = f"{Config.SF_DATA_API_BASE}/{dataset_id}.json"
    
    params = {
        "$limit": limit,
        "$order": "record_id DESC"
    }
    
    if Config.SF_DATA_APP_TOKEN:
        params["$$app_token"] = Config.SF_DATA_APP_TOKEN
    
    try:
        logger.info(f"Downloading data from {url}")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved raw data to {output_path}")
        
        df = pd.DataFrame(data)
        logger.info(f"Downloaded {len(df)} records from dataset {dataset_id}")
        
        return df
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading data: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

def download_business_registry(output_path: Optional[Path] = None) -> pd.DataFrame:
    """Download SF Business Registry data"""
    path = output_path or Config.RAW_DATA_DIR / "business_registry.json"
    return download_sf_data(Config.BUSINESS_LICENSE_DATASET, path)

def download_permits(output_path: Optional[Path] = None) -> pd.DataFrame:
    """Download Building Permits data"""
    path = output_path or Config.RAW_DATA_DIR / "permits.json"
    return download_sf_data(Config.PERMITS_DATASET, path)

def download_complaints(output_path: Optional[Path] = None) -> pd.DataFrame:
    """Download Code Enforcement Complaints data"""
    path = output_path or Config.RAW_DATA_DIR / "complaints.json"
    return download_sf_data(Config.COMPLAINTS_DATASET, path)
