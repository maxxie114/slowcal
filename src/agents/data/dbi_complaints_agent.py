"""
DBI Complaints Agent

Fetches building complaints from DBI Complaints (All Divisions) dataset.
Provides code enforcement signals for risk assessment.

Dataset: gm2e-bten (DBI Complaints - All Divisions)
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base_agent import BaseDataAgent, AgentOutput

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.config import Config
from tools.socrata_client import sanitize_for_soql, extract_address_components

logger = logging.getLogger(__name__)


class DBIComplaintsAgent(BaseDataAgent):
    """
    Agent for querying SF DBI Complaints data.
    
    Returns building complaint signals:
    - dbi_count_3m/6m/12m: Time-windowed complaint counts
    - division_breakdown: Complaints by DBI division
    - open_closed_ratio: Ratio of open to closed complaints
    - complaint_types: Distribution of complaint types
    """
    
    VERSION = "0.1"
    
    @property
    def name(self) -> str:
        return "DBIComplaintsAgent"
    
    @property
    def dataset_id(self) -> str:
        return Config.DBI_COMPLAINTS_DATASET
    
    def fetch_signals(
        self,
        entity_id: str = None,
        address: str = None,
        lat: float = None,
        lon: float = None,
        neighborhood: str = None,
        as_of: datetime = None,
        horizon_months: int = 6,
    ) -> AgentOutput:
        """
        Fetch DBI complaint signals for a location.
        """
        as_of = as_of or datetime.utcnow()
        data_gaps = []
        evidence_refs = []
        
        if not address and not (lat and lon):
            data_gaps.append("No address or location provided")
            return self.create_output(
                signals=self._empty_signals(),
                evidence_refs=[],
                data_gaps=data_gaps,
            )
        
        try:
            # Query complaints for different time windows
            count_3m = self._get_complaint_count(address, lat, lon, 3, as_of)
            count_6m = self._get_complaint_count(address, lat, lon, 6, as_of)
            count_12m = self._get_complaint_count(address, lat, lon, 12, as_of)
            
            # Generate evidence refs
            ref_3m = self.generate_evidence_ref("dbi")
            ref_6m = self.generate_evidence_ref("dbi")
            ref_12m = self.generate_evidence_ref("dbi")
            evidence_refs.extend([ref_3m, ref_6m, ref_12m])
            
            # Get division breakdown
            divisions = self._get_division_breakdown(address, lat, lon, 12, as_of)
            div_ref = self.generate_evidence_ref("dbi")
            evidence_refs.append(div_ref)
            
            # Get status distribution
            status_data = self._get_status_distribution(address, lat, lon, 12, as_of)
            
            # Compute trend
            trend = self.compute_trend(count_3m, count_6m, count_12m)
            
            signals = {
                "dbi_count_3m": count_3m,
                "dbi_count_6m": count_6m,
                "dbi_count_12m": count_12m,
                "dbi_trend": trend,
                "division_breakdown": divisions,
                "open_complaints": status_data.get("open", 0),
                "closed_complaints": status_data.get("closed", 0),
                "open_closed_ratio": self._safe_ratio(
                    status_data.get("open", 0),
                    status_data.get("closed", 1)
                ),
                "has_open_violations": status_data.get("open", 0) > 0,
                "evidence_map": {
                    "count_3m": ref_3m,
                    "count_6m": ref_6m,
                    "count_12m": ref_12m,
                    "divisions": div_ref,
                },
            }
            
        except Exception as e:
            logger.error(f"Error fetching DBI signals: {e}")
            data_gaps.append(f"Query error: {str(e)}")
            return self.create_output(
                signals=self._empty_signals(),
                evidence_refs=[],
                data_gaps=data_gaps,
            )
        
        return self.create_output(
            signals=signals,
            evidence_refs=evidence_refs,
            data_gaps=data_gaps,
        )
    
    def _empty_signals(self) -> Dict[str, Any]:
        return {
            "dbi_count_3m": 0,
            "dbi_count_6m": 0,
            "dbi_count_12m": 0,
            "dbi_trend": "stable",
            "division_breakdown": [],
            "open_complaints": 0,
            "closed_complaints": 0,
            "open_closed_ratio": 0,
            "has_open_violations": False,
        }
    
    def _safe_ratio(self, numerator: int, denominator: int) -> float:
        if denominator == 0:
            return 0.0
        return round(numerator / denominator, 2)
    
    def _get_complaint_count(
        self,
        address: str,
        lat: float,
        lon: float,
        months_back: int,
        as_of: datetime,
    ) -> int:
        """Get DBI complaint count for time window"""
        start_date = as_of - timedelta(days=months_back * 30)
        
        # DBI complaints use date_filed field and separate street_number/street_name fields
        where = f"date_filed >= '{start_date.strftime('%Y-%m-%dT%H:%M:%S')}'"
        
        if address:
            # Extract and sanitize address components
            addr_parts = extract_address_components(address)
            if addr_parts["street_number"] and addr_parts["street_name"]:
                # Query using separate street_number and street_name fields
                street_name_clean = addr_parts['street_name'].split()[0] if addr_parts['street_name'] else ""
                where = f"({where}) AND street_number = '{addr_parts['street_number']}' AND upper(street_name) LIKE '%{street_name_clean[:15]}%'"
            elif addr_parts["street_name"]:
                # Just use street name
                street_name_clean = addr_parts['street_name'].split()[0] if addr_parts['street_name'] else ""
                where = f"({where}) AND upper(street_name) LIKE '%{street_name_clean[:15]}%'"
        elif lat and lon:
            # Use spatial query if available
            try:
                result = self.client.query_spatial(
                    dataset_id=self.dataset_id,
                    lat=lat,
                    lon=lon,
                    radius_meters=Config.DEFAULT_SEARCH_RADIUS_METERS,
                    point_field="location",
                    date_field="file_date",
                    months_back=months_back,
                    select="count(*) as count",
                    as_of=as_of,
                )
                if result.data and len(result.data) > 0:
                    return int(result.data[0].get("count", 0))
            except Exception:
                pass  # Fall back to non-spatial query
        
        result = self.client.query(
            self.dataset_id,
            f"$select=count(*) as count&$where={where}",
        )
        
        if result.data and len(result.data) > 0:
            return int(result.data[0].get("count", 0))
        return 0
    
    def _get_division_breakdown(
        self,
        address: str,
        lat: float,
        lon: float,
        months_back: int,
        as_of: datetime,
    ) -> List[Dict[str, Any]]:
        """Get complaints breakdown by DBI division"""
        start_date = as_of - timedelta(days=months_back * 30)
        
        where = f"date_filed >= '{start_date.strftime('%Y-%m-%dT%H:%M:%S')}'"
        if address:
            addr_parts = extract_address_components(address)
            if addr_parts["street_number"] and addr_parts["street_name"]:
                street_name_clean = addr_parts['street_name'].split()[0] if addr_parts['street_name'] else ""
                where = f"({where}) AND street_number = '{addr_parts['street_number']}' AND upper(street_name) LIKE '%{street_name_clean[:15]}%'"
            elif addr_parts["street_name"]:
                street_name_clean = addr_parts['street_name'].split()[0] if addr_parts['street_name'] else ""
                where = f"({where}) AND upper(street_name) LIKE '%{street_name_clean[:15]}%'"
        
        result = self.client.query(
            self.dataset_id,
            f"$select=receiving_division as division, count(*) as count&$where={where}&$group=receiving_division&$order=count DESC&$limit=10",
        )
        
        return [
            {"division": r.get("division"), "count": int(r.get("count", 0))}
            for r in result.data
        ]
    
    def _get_status_distribution(
        self,
        address: str,
        lat: float,
        lon: float,
        months_back: int,
        as_of: datetime,
    ) -> Dict[str, int]:
        """Get open/closed status counts"""
        start_date = as_of - timedelta(days=months_back * 30)
        
        where = f"date_filed >= '{start_date.strftime('%Y-%m-%dT%H:%M:%S')}'"
        if address:
            addr_parts = extract_address_components(address)
            if addr_parts["street_number"] and addr_parts["street_name"]:
                street_name_clean = addr_parts['street_name'].split()[0] if addr_parts['street_name'] else ""
                where = f"({where}) AND street_number = '{addr_parts['street_number']}' AND upper(street_name) LIKE '%{street_name_clean[:15]}%'"
            elif addr_parts["street_name"]:
                street_name_clean = addr_parts['street_name'].split()[0] if addr_parts['street_name'] else ""
                where = f"({where}) AND upper(street_name) LIKE '%{street_name_clean[:15]}%'"
        
        result = self.client.query(
            self.dataset_id,
            f"$select=status, count(*) as count&$where={where}&$group=status",
        )
        
        status_counts = {"open": 0, "closed": 0}
        for r in result.data:
            status = str(r.get("status", "")).lower()
            count = int(r.get("count", 0))
            if "open" in status or "active" in status or "pending" in status:
                status_counts["open"] += count
            elif "closed" in status or "complete" in status:
                status_counts["closed"] += count
        
        return status_counts
