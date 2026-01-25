"""
Fix for SF.gov API Download Issue

The original code was failing because it tried to order by 'record_id DESC',
but the dataset doesn't have a 'record_id' field.

This script provides the corrected download function.
"""

import requests
import json
import pandas as pd
from pathlib import Path
from typing import Optional


def download_sf_data(url: str, output_path: Optional[Path] = None, limit: int = 50000) -> pd.DataFrame:
    """
    Download data from SF.gov Open Data API
    
    Args:
        url: Full API endpoint URL
        output_path: Optional path to save raw JSON
        limit: Maximum records to download
    
    Returns:
        DataFrame with downloaded data
    """
    # FIXED: Removed the invalid $order parameter
    params = {
        "$limit": limit
    }
    
    try:
        print(f"  ⬇️ Downloading from {url}...")
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"  💾 Saved to {output_path}")
        
        df = pd.DataFrame(data)
        print(f"  ✅ Downloaded {len(df):,} records")
        return df
    
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return pd.DataFrame()


# Alternative: If you want to order by a valid field, use one of these:
def download_sf_data_ordered(url: str, output_path: Optional[Path] = None, limit: int = 50000) -> pd.DataFrame:
    """
    Download data from SF.gov Open Data API with ordering
    
    Uses 'certificate_number' for ordering since 'record_id' doesn't exist
    """
    params = {
        "$limit": limit,
        "$order": "certificate_number DESC"  # Use a valid field
    }
    
    try:
        print(f"  ⬇️ Downloading from {url}...")
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"  💾 Saved to {output_path}")
        
        df = pd.DataFrame(data)
        print(f"  ✅ Downloaded {len(df):,} records")
        return df
    
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return pd.DataFrame()


if __name__ == "__main__":
    # Test the fixed function
    print("🧪 Testing fixed download function...")
    print("="*60)
    
    test_url = 'https://data.sfgov.org/resource/g8m3-pdis.json'
    
    # Test with small limit first
    df = download_sf_data(test_url, limit=10)
    
    if len(df) > 0:
        print("\n✅ SUCCESS! API is working now.")
        print(f"\n📊 Downloaded {len(df)} records")
        print(f"📋 Columns: {list(df.columns)}")
        print(f"\n👀 Sample data:")
        print(df.head())
    else:
        print("\n❌ Still having issues. Check your internet connection.")
