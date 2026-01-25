
"""
Supabase Evidence Client

Adapter that mimics the SocrataClient interface but queries
Supabase tables (permits, violations, complaints_311, sfpd_incidents)
instead of Socrata datasets.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import re

from supabase import create_client, Client
from utils.config import Config

logger = logging.getLogger(__name__)

# Re-use SyntheticQueryResult structure for compatibility
class SupabaseQueryResult:
    def __init__(self, data: List[Dict[str, Any]], dataset_id: str):
        self.data = data
        self.dataset_id = dataset_id
        self.pulled_at = datetime.utcnow()
        self.record_count = len(data)

class SupabaseEvidenceClient:
    """
    Adapter to query Supabase evidence tables using Socrata-style methods.
    """
    
    def __init__(self):
        url = "https://lvlkgssnfmszujxtrasa.supabase.co"
        key = "sb_publishable_l8Cx8bsqkPZ-B_q3ka6MmQ_JspTcv30"
        self.client = create_client(url, key)
        
        # Mappings from Socrata dataset ID to Supabase table name
        self.table_map = {
            Config.BUSINESS_LICENSE_DATASET: "master_model_data", # Use master for registry
            Config.PERMITS_DATASET: "permits",
            "nhtv-bhqe": "violations", # DBI Complaints
            Config.COMPLAINTS_311_DATASET: "complaints_311",
            Config.SFPD_INCIDENTS_DATASET: "sfpd_incidents",
            Config.EVICTIONS_DATASET: "evictions", # If exists
            Config.TAXABLE_COMMERCIAL_SPACES_DATASET: "vacancy" # If exists
        }

    def query(self, dataset_id: str, soql: str = "", **kwargs) -> SupabaseQueryResult:
        """
        Execute query against Supabase equivalent table.
        Parses basic SOQL WHERE clauses to Supabase filters.
        """
        table_name = self.table_map.get(dataset_id)
        if not table_name:
            logger.warning(f"No Supabase table mapped for dataset {dataset_id}")
            return SupabaseQueryResult([], dataset_id)
            
        query_builder = self.client.table(table_name).select("*")
        
        # Simple SOQL Parser for Filters
        # Only supports simple equality and LIKE for business_id/address
        # Agents mostly use: where business_id='...' or address like '...'
        
        # 1. Business ID / Unique ID
        id_match = re.search(r"(?:uniqueid|id|business_account_number|business_id)\s*=\s*'([^']+)'", soql, re.IGNORECASE)
        if id_match:
            business_id = id_match.group(1)
            # Try matching columns that might hold the ID
            # For master_model_data it's 'id', for others 'business_id'
            if table_name == "master_model_data":
                query_builder = query_builder.eq("id", business_id)
            else:
                query_builder = query_builder.eq("business_id", business_id)
                
        # 2. Limit
        limit_match = re.search(r"\$limit=(\d+)", soql)
        limit = int(limit_match.group(1)) if limit_match else 100
        
        # Execute
        try:
            response = query_builder.limit(limit).execute()
            return SupabaseQueryResult(response.data, dataset_id)
        except Exception as e:
            logger.error(f"Supabase query failed for {table_name}: {e}")
            return SupabaseQueryResult([], dataset_id)

    def query_spatial(self, dataset_id: str, lat: float, lon: float, radius_meters: int = 100, **kwargs) -> SupabaseQueryResult:
        """
        Spatial query adapter.
        Since Supabase tables currently store location as JSONB or simple columns,
        and we don't have PostGIS enabled on public interface easily without RPC,
        we will fetch records and filtering client-side for this MVP.
        
        Or use basic bounding box if lat/lon columns exist. 
        Synthetic data tables have 'location' -> {'latitude': ..., 'longitude': ...}
        """
        table_name = self.table_map.get(dataset_id)
        if not table_name:
            return SupabaseQueryResult([], dataset_id)
            
        # Optimization: Filter by roughly matching lat/lon first (bounding box)
        # 1 degree lat approx 111km. 100m is approx 0.001 degrees.
        # Let's grab a 0.02 degree box (~2km) to be safe and filter locally.
        box_size = 0.02
        
        # Check if table has flat lat/lon or jsonb
        # Synthetic data: location->latitude 
        # But we assume we can't do complex JSON filtering easily on REST without generated columns.
        # So we just fetch recent items and filter.
        
        try:
            # Hard limit to avoid fetching too much
            response = self.client.table(table_name).select("*").limit(500).execute()
            candidates = response.data
            
            # Client-side filtering
            results = []
            for record in candidates:
                r_lat, r_lon = None, None
                
                # Check JSONB location
                loc = record.get("location")
                if isinstance(loc, dict):
                    r_lat = loc.get("latitude")
                    r_lon = loc.get("longitude")
                
                # Check flat columns
                if r_lat is None:
                    r_lat = record.get("latitude") or record.get("lat")
                if r_lon is None:
                    r_lon = record.get("longitude") or record.get("lon")
                    
                if r_lat is not None and r_lon is not None:
                    try:
                        # Simple Euclidean distance for speed (small radius)
                        # dist_sq = (lat - r_lat)^2 + (lon - r_lon)^2
                        dist_deg = ((lat - float(r_lat))**2 + (lon - float(r_lon))**2)**0.5
                        # 0.001 deg approx 100m
                        if dist_deg < (radius_meters / 100000.0): 
                            results.append(record)
                    except:
                        pass
                        
            return SupabaseQueryResult(results, dataset_id)
            
        except Exception as e:
            logger.error(f"Supabase spatial query failed: {e}")
            return SupabaseQueryResult([], dataset_id)

    def query_time_window(self, dataset_id: str, **kwargs) -> SupabaseQueryResult:
        return self.query(dataset_id, **kwargs)
