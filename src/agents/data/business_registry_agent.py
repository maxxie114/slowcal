"""
Business Registry Agent

Fetches business registration data from SF Registered Business Locations dataset.
Provides canonical business records, locations, and key dates.

Dataset: g8m3-pdis (Registered Business Locations - San Francisco)
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base_agent import BaseDataAgent, AgentOutput

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.config import Config

logger = logging.getLogger(__name__)


class BusinessRegistryAgent(BaseDataAgent):
    """
    Agent for querying SF Registered Business Locations.
    
    Returns canonical business records including:
    - Business name and DBA
    - Address and location
    - Registration dates
    - NAIC codes (industry classification)
    - Active status
    """
    
    VERSION = "0.1"
    
    @property
    def name(self) -> str:
        return "BusinessRegistryAgent"
    
    @property
    def dataset_id(self) -> str:
        return Config.BUSINESS_LICENSE_DATASET
    
    def fetch_signals(
        self,
        entity_id: str = None,
        address: str = None,
        lat: float = None,
        lon: float = None,
        neighborhood: str = None,
        as_of: datetime = None,
        horizon_months: int = 6,
        business_name: str = None,
    ) -> AgentOutput:
        """
        Fetch business registry data.
        
        Searches by business name, address, or location.
        """
        as_of = as_of or datetime.utcnow()
        data_gaps = []
        evidence_refs = []
        
        # Build query based on available identifiers
        results = []
        
        if business_name:
            results = self._search_by_name(business_name)
        elif address:
            results = self._search_by_address(address)
        elif lat and lon:
            results = self._search_by_location(lat, lon)
        else:
            data_gaps.append("No search criteria provided (name, address, or location)")
            return self.create_output(
                signals={"candidates": [], "primary": None},
                evidence_refs=[],
                data_gaps=data_gaps,
            )
        
        # Process results
        candidates = []
        for record in results[:10]:  # Limit to top 10 candidates
            ref = self.generate_evidence_ref("biz")
            evidence_refs.append(ref)
            
            candidate = self._parse_business_record(record)
            candidate["evidence_ref"] = ref
            candidates.append(candidate)
        
        # Select primary candidate (best match)
        primary = candidates[0] if candidates else None
        
        signals = {
            "candidates": candidates,
            "primary": primary,
            "total_matches": len(results),
        }
        
        if not candidates:
            data_gaps.append(f"No business records found for query")
        
        return self.create_output(
            signals=signals,
            evidence_refs=evidence_refs,
            data_gaps=data_gaps,
        )
    
    def _search_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Search by business name or DBA"""
        normalized = name.upper().strip()
        
        soql = f"""$select=*
&$where=upper(dba_name) LIKE '%{normalized}%' OR upper(ownership_name) LIKE '%{normalized}%'
&$order=location_start_date DESC
&$limit=20"""
        
        result = self.client.query(self.dataset_id, soql.replace('\n', ''))
        return result.data
    
    def _search_by_address(self, address: str) -> List[Dict[str, Any]]:
        """Search by street address"""
        normalized = address.upper().strip()
        
        soql = f"""$select=*
&$where=upper(full_business_address) LIKE '%{normalized}%'
&$order=location_start_date DESC
&$limit=20"""
        
        result = self.client.query(self.dataset_id, soql.replace('\n', ''))
        return result.data
    
    def _search_by_location(self, lat: float, lon: float, radius: int = 100) -> List[Dict[str, Any]]:
        """Search by geographic location"""
        result = self.client.query_spatial(
            dataset_id=self.dataset_id,
            lat=lat,
            lon=lon,
            radius_meters=radius,
            point_field="business_location",
            select="*",
            order="location_start_date DESC",
            limit=20,
        )
        return result.data
    
    def _parse_business_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw record into structured business data"""
        # Extract location coordinates if available
        location = record.get("business_location", {})
        lat = None
        lon = None
        
        if isinstance(location, dict):
            lat = location.get("latitude")
            lon = location.get("longitude")
        
        # Parse dates
        start_date = record.get("location_start_date")
        end_date = record.get("location_end_date")
        
        # Determine active status
        is_active = end_date is None or end_date == ""
        
        return {
            "business_name": record.get("dba_name") or record.get("ownership_name"),
            "ownership_name": record.get("ownership_name"),
            "dba_name": record.get("dba_name"),
            "address": record.get("full_business_address"),
            "city": record.get("city"),
            "state": record.get("state"),
            "zip": record.get("business_zip"),
            "neighborhood": record.get("neighborhoods_analysis_boundaries"),
            "latitude": float(lat) if lat else None,
            "longitude": float(lon) if lon else None,
            "naic_code": record.get("naic_code"),
            "naic_description": record.get("naic_code_description"),
            "location_start_date": start_date,
            "location_end_date": end_date,
            "is_active": is_active,
            "business_id": record.get("uniqueid") or record.get("ttxid"),
            "parking_tax": record.get("parking_tax") == "Y",
            "transient_tax": record.get("transient_occupancy_tax") == "Y",
            "supervisor_district": record.get("supervisor_district"),
        }
    
    def get_business_by_id(self, business_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a specific business by ID"""
        soql = f"$where=uniqueid='{business_id}' OR ttxid='{business_id}'"
        result = self.client.query(self.dataset_id, soql)
        
        if result.data:
            return self._parse_business_record(result.data[0])
        return None
    
    def get_businesses_in_neighborhood(
        self,
        neighborhood: str,
        active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Get all businesses in a neighborhood"""
        where = f"neighborhoods_analysis_boundaries='{neighborhood}'"
        if active_only:
            where = f"({where}) AND location_end_date IS NULL"
        
        soql = f"$where={where}&$limit=1000"
        result = self.client.query(self.dataset_id, soql)
        
        return [self._parse_business_record(r) for r in result.data]
