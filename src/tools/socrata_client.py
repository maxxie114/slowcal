"""
Socrata/SODA API Client for DataSF Queries

Provides SoQL query interface for San Francisco Open Data datasets.
Supports:
- Time-windowed aggregations (3/6/12 month)
- Spatial queries (within_circle)
- Caching with freshness tracking
"""

import logging
import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

import requests
from requests.exceptions import RequestException

import sys
sys.path.append(str(Path(__file__).parent.parent))
from utils.config import Config

logger = logging.getLogger(__name__)


def sanitize_for_soql(value: str) -> str:
    """
    Sanitize a string value for use in SoQL queries.
    
    - Escapes single quotes (SoQL string delimiter)
    - Removes special characters that cause 400 errors
    - Normalizes whitespace
    
    Args:
        value: Raw string value
        
    Returns:
        Sanitized string safe for SoQL
    """
    if not value:
        return ""
    
    # Escape single quotes by doubling them (SoQL standard)
    sanitized = value.replace("'", "''")
    
    # Remove problematic characters for LIKE patterns
    # Keep alphanumeric, spaces, and common address chars
    sanitized = re.sub(r'[^\w\s\-\#\.]', ' ', sanitized)
    
    # Normalize whitespace
    sanitized = ' '.join(sanitized.split())
    
    return sanitized.strip()


def extract_address_components(address: str) -> Dict[str, str]:
    """
    Extract street number and street name from an address string.
    
    Args:
        address: Full address string like "300 Webster St, SF"
        
    Returns:
        Dict with 'street_number' and 'street_name' keys
    """
    if not address:
        return {"street_number": "", "street_name": ""}
    
    # Clean up the address
    cleaned = address.upper().strip()
    
    # Remove city/state suffix patterns
    cleaned = re.sub(r',?\s*(SAN FRANCISCO|SF|CA|CALIFORNIA).*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip(' ,')
    
    # Try to extract street number and name
    match = re.match(r'^(\d+)\s+(.+)$', cleaned)
    if match:
        return {
            "street_number": match.group(1),
            "street_name": sanitize_for_soql(match.group(2))
        }
    
    return {
        "street_number": "",
        "street_name": sanitize_for_soql(cleaned)
    }


@dataclass
class QueryResult:
    """Result from a Socrata query with metadata"""
    data: List[Dict[str, Any]]
    dataset_id: str
    query: str
    pulled_at: datetime
    record_count: int
    cache_hit: bool = False
    data_gaps: List[str] = field(default_factory=list)
    
    def to_evidence_ref(self) -> Dict[str, Any]:
        """Generate evidence reference for audit trail"""
        return {
            "dataset_id": self.dataset_id,
            "pulled_at": self.pulled_at.isoformat(),
            "record_count": self.record_count,
            "query_hash": hashlib.md5(self.query.encode()).hexdigest()[:8],
        }


class SocrataClient:
    """
    Client for Socrata SODA API with SoQL support.
    
    Example usage:
        client = SocrataClient()
        
        # Simple query
        result = client.query("vw6y-z8j6", "$limit=100")
        
        # Time-windowed query
        result = client.query_time_window(
            "vw6y-z8j6",
            months_back=6,
            date_field="case_created_date",
            select="category,count(*)",
            group="category"
        )
        
        # Spatial query
        result = client.query_spatial(
            "vw6y-z8j6",
            lat=37.7749,
            lon=-122.4194,
            radius_meters=500,
            date_field="case_created_date",
            months_back=6
        )
    """
    
    def __init__(
        self,
        base_url: str = None,
        app_token: str = None,
        cache_dir: Path = None,
        cache_ttl_hours: int = 24,
    ):
        self.base_url = base_url or Config.SF_DATA_API_BASE
        self.app_token = app_token or Config.SF_DATA_APP_TOKEN
        self.cache_dir = cache_dir or Config.RAW_DATA_DIR / "cache"
        self.cache_ttl_hours = cache_ttl_hours
        
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def query(
        self,
        dataset_id: str,
        soql: str = "",
        limit: int = 50000,
        use_cache: bool = True,
    ) -> QueryResult:
        """
        Execute a SoQL query against a Socrata dataset.
        
        Args:
            dataset_id: Socrata dataset identifier (e.g., 'vw6y-z8j6')
            soql: SoQL query string (e.g., '$select=category&$limit=100')
            limit: Maximum records to return
            use_cache: Whether to use cached results
        
        Returns:
            QueryResult with data and metadata
        """
        # Build full query
        query_parts = [soql] if soql else []
        if f"$limit" not in soql.lower():
            query_parts.append(f"$limit={limit}")
        
        full_query = "&".join(query_parts)
        
        # Check cache
        cache_key = self._get_cache_key(dataset_id, full_query)
        if use_cache:
            # NOTE: Local file override is DISABLED for regular queries.
            # The local file override was causing ALL queries to return cached data
            # instead of executing the actual SoQL query. Agents that need local file
            # access (like VacancyCorridorAgent) should load files directly.
            
            cached = self._get_cached(cache_key)
            if cached:
                return cached
        
        # Execute query
        url = f"{self.base_url}/{dataset_id}.json"
        params = self._parse_soql_params(full_query)
        
        if self.app_token:
            params["$$app_token"] = self.app_token
        
        try:
            logger.info(f"Querying Socrata: {dataset_id} with {len(params)} params")
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            
            result = QueryResult(
                data=data,
                dataset_id=dataset_id,
                query=full_query,
                pulled_at=datetime.utcnow(),
                record_count=len(data),
                cache_hit=False,
            )
            
            # Cache result
            if use_cache:
                self._set_cached(cache_key, result)
            
            logger.info(f"Retrieved {len(data)} records from {dataset_id}")
            return result
            
        except RequestException as e:
            logger.error(f"Socrata query failed: {e}")
            
            # Try cache fallback
            cached = self._get_cached(cache_key, ignore_ttl=True)
            if cached:
                logger.warning(f"Using stale cache for {dataset_id}")
                cached.data_gaps.append(f"Stale data: network error at {datetime.utcnow().isoformat()}")
                return cached
            
            raise ConnectionError(f"Failed to query {dataset_id}: {e}") from e
    
    def query_time_window(
        self,
        dataset_id: str,
        months_back: int,
        date_field: str,
        select: str = "*",
        where: str = "",
        group: str = "",
        order: str = "",
        limit: int = 50000,
        as_of: datetime = None,
    ) -> QueryResult:
        """
        Query with a time window filter.
        
        Args:
            dataset_id: Socrata dataset ID
            months_back: Number of months to look back
            date_field: Name of the date field to filter
            select: SoQL $select clause
            where: Additional SoQL $where conditions
            group: SoQL $group clause
            order: SoQL $order clause
            limit: Maximum records
            as_of: Reference date (defaults to now)
        
        Returns:
            QueryResult with time-filtered data
        """
        as_of = as_of or datetime.utcnow()
        start_date = as_of - timedelta(days=months_back * 30)
        
        # Build time filter
        time_filter = f"{date_field} >= '{start_date.strftime('%Y-%m-%dT%H:%M:%S')}'"
        if where:
            where = f"({time_filter}) AND ({where})"
        else:
            where = time_filter
        
        # Build SoQL
        soql_parts = [f"$select={select}", f"$where={where}"]
        if group:
            soql_parts.append(f"$group={group}")
        if order:
            soql_parts.append(f"$order={order}")
        soql_parts.append(f"$limit={limit}")
        
        soql = "&".join(soql_parts)
        return self.query(dataset_id, soql, limit=limit)
    
    def query_spatial(
        self,
        dataset_id: str,
        lat: float,
        lon: float,
        radius_meters: int = 500,
        point_field: str = "point",
        date_field: str = None,
        months_back: int = None,
        select: str = "*",
        where: str = "",
        group: str = "",
        order: str = "",
        limit: int = 50000,
        as_of: datetime = None,
    ) -> QueryResult:
        """
        Query with spatial filter (within_circle).
        
        Args:
            dataset_id: Socrata dataset ID
            lat: Latitude center point
            lon: Longitude center point
            radius_meters: Search radius in meters
            point_field: Name of the point/location field
            date_field: Optional date field for time filtering
            months_back: Optional months to look back
            select: SoQL $select clause
            where: Additional SoQL $where conditions
            group: SoQL $group clause
            order: SoQL $order clause
            limit: Maximum records
            as_of: Reference date
        
        Returns:
            QueryResult with spatially-filtered data
        """
        # Build spatial filter
        spatial_filter = f"within_circle({point_field}, {lat}, {lon}, {radius_meters})"
        
        # Combine with time filter if provided
        filters = [spatial_filter]
        if date_field and months_back:
            as_of = as_of or datetime.utcnow()
            start_date = as_of - timedelta(days=months_back * 30)
            time_filter = f"{date_field} >= '{start_date.strftime('%Y-%m-%dT%H:%M:%S')}'"
            filters.append(time_filter)
        
        if where:
            filters.append(f"({where})")
        
        full_where = " AND ".join(filters)
        
        # Build SoQL
        soql_parts = [f"$select={select}", f"$where={full_where}"]
        if group:
            soql_parts.append(f"$group={group}")
        if order:
            soql_parts.append(f"$order={order}")
        soql_parts.append(f"$limit={limit}")
        
        soql = "&".join(soql_parts)
        return self.query(dataset_id, soql, limit=limit)
    
    def get_dataset_freshness(self, dataset_id: str) -> Dict[str, Any]:
        """
        Check dataset metadata for freshness information.
        
        Returns:
            Dict with last_updated, update_frequency, etc.
        """
        # Socrata metadata endpoint
        url = f"https://data.sfgov.org/api/views/{dataset_id}.json"
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            metadata = response.json()
            
            return {
                "dataset_id": dataset_id,
                "name": metadata.get("name"),
                "last_updated": metadata.get("rowsUpdatedAt"),
                "created_at": metadata.get("createdAt"),
                "row_count": metadata.get("rowCount"),
                "description": metadata.get("description"),
            }
        except RequestException as e:
            logger.warning(f"Could not fetch metadata for {dataset_id}: {e}")
            return {"dataset_id": dataset_id, "error": str(e)}
    
    def _parse_soql_params(self, soql: str) -> Dict[str, str]:
        """Parse SoQL string into request parameters"""
        params = {}
        if not soql:
            return params
        
        for part in soql.split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                params[key] = value
        
        return params
    
    def _get_cache_key(self, dataset_id: str, query: str) -> str:
        """Generate cache key from dataset and query"""
        query_hash = hashlib.md5(query.encode()).hexdigest()[:12]
        return f"{dataset_id}_{query_hash}"
    
    def _get_cached(self, cache_key: str, ignore_ttl: bool = False) -> Optional[QueryResult]:
        """Retrieve cached result if valid"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, "r") as f:
                cached_data = json.load(f)
            
            pulled_at = datetime.fromisoformat(cached_data["pulled_at"])
            
            # Check TTL
            if not ignore_ttl:
                age_hours = (datetime.utcnow() - pulled_at).total_seconds() / 3600
                if age_hours > self.cache_ttl_hours:
                    return None
            
            return QueryResult(
                data=cached_data["data"],
                dataset_id=cached_data["dataset_id"],
                query=cached_data["query"],
                pulled_at=pulled_at,
                record_count=cached_data["record_count"],
                cache_hit=True,
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Invalid cache file {cache_key}: {e}")
            return None
    
    def _set_cached(self, cache_key: str, result: QueryResult) -> None:
        """Store result in cache"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            with open(cache_file, "w") as f:
                json.dump({
                    "data": result.data,
                    "dataset_id": result.dataset_id,
                    "query": result.query,
                    "pulled_at": result.pulled_at.isoformat(),
                    "record_count": result.record_count,
                }, f)
        except Exception as e:
            logger.warning(f"Failed to cache result: {e}")


# Convenience function for simple queries
def socrata_query(
    dataset_id: str,
    soql: str = "",
    app_token: str = None,
) -> List[Dict[str, Any]]:
    """
    Simple function interface for Socrata queries.
    
    Args:
        dataset_id: Socrata dataset ID
        soql: SoQL query string
        app_token: Optional app token (uses Config default)
    
    Returns:
        List of record dictionaries
    """
    client = SocrataClient(app_token=app_token)
    result = client.query(dataset_id, soql)
    return result.data
