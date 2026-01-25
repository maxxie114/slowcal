"""
Download data from SF.gov Open Data API
"""

import json
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from requests.exceptions import RequestException

from utils.config import Config
import logging

logger = logging.getLogger(__name__)

def _read_cached_json(path: Path) -> pd.DataFrame:
    """Read a cached JSON file (list of records) into a DataFrame."""
    if not path.exists():
        raise FileNotFoundError(f"No cached file at {path}")
    return pd.read_json(path, orient="records")


def download_sf_data(
    dataset_id: str,
    output_path: Optional[Path] = None,
    limit: int = 50000,
    allow_fail: bool = False,
) -> pd.DataFrame:
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

    # Don't use $order by default — column names vary per dataset
    params = {"$limit": limit}
    if Config.SF_DATA_APP_TOKEN:
        params["$$app_token"] = Config.SF_DATA_APP_TOKEN

    # If a cached file exists and network is flaky, prefer the cache when appropriate
    if output_path and Path(output_path).exists():
        try:
            logger.info("Found cached data at %s, loading cached file", output_path)
            return _read_cached_json(output_path)
        except Exception:
            logger.debug("Failed to read cached file at %s", output_path)

    try:
        logger.info(f"Downloading data from {url}")
        response = requests.get(url, params=params, timeout=30)

        if response.status_code != 200:
            msg = f"HTTP {response.status_code} for {url}: {response.text[:200]}"
            logger.error(msg)
            # Fallback to cache if available
            if output_path and Path(output_path).exists():
                logger.info("Using cached file due to HTTP error")
                return _read_cached_json(output_path)
            if allow_fail:
                logger.warning("allow_fail=True: returning empty DataFrame due to HTTP error")
                return pd.DataFrame()
            response.raise_for_status()

        data = response.json()

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved raw data to {output_path}")

        df = pd.DataFrame(data)
        logger.info(f"Downloaded {len(df)} records from dataset {dataset_id}")

        return df

    except RequestException as exc:
        logger.warning("Network error while fetching %s: %s", url, exc)
        if output_path and Path(output_path).exists():
            logger.info("Network failed: loading cached file at %s", output_path)
            return _read_cached_json(output_path)
        if allow_fail:
            logger.warning("allow_fail=True: returning empty DataFrame due to network error")
            return pd.DataFrame()
        raise ConnectionError(
            f"Failed to retrieve data from {url}. Network/DNS error: {exc}. "
            f"If you're offline, place a cached file at {output_path} or call the function with allow_fail=True."
        ) from exc

def download_business_registry(output_path: Optional[Path] = None, allow_fail: bool = False) -> pd.DataFrame:
    """Download SF Business Registry data"""
    path = output_path or Config.RAW_DATA_DIR / "business_registry.json"
    return download_sf_data(Config.BUSINESS_LICENSE_DATASET, path, allow_fail=allow_fail)

def download_permits(output_path: Optional[Path] = None, allow_fail: bool = False) -> pd.DataFrame:
    """Download Building Permits data"""
    path = output_path or Config.RAW_DATA_DIR / "permits.json"
    return download_sf_data(Config.PERMITS_DATASET, path, allow_fail=allow_fail)

def download_complaints(output_path: Optional[Path] = None, allow_fail: bool = False) -> pd.DataFrame:
    """Download Code Enforcement Complaints data"""
    path = output_path or Config.RAW_DATA_DIR / "complaints.json"
    return download_sf_data(Config.COMPLAINTS_DATASET, path, allow_fail=allow_fail)
