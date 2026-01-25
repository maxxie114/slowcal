"""
Permits Agent

Fetches building permit data from SF Building Permits dataset.
Provides permit activity signals for risk assessment.

Dataset: i98e-djp9 (Building Permits)
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base_agent import BaseDataAgent, AgentOutput

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.config import Config

logger = logging.getLogger(__name__)


class PermitsAgent(BaseDataAgent):
    """
    Agent for querying SF Building Permits data.
    
    Returns permit activity signals:
    - permit_count_3m/6m/12m: Time-windowed permit counts
    - avg_permit_cost_12m: Average permit valuation
    - permit_trend: Direction of permit activity
    - permit_types: Distribution of permit types
    """
    
    VERSION = "0.1"
    
    @property
    def name(self) -> str:
        return "PermitsAgent"
    
    @property
    def dataset_id(self) -> str:
        return Config.PERMITS_DATASET
    
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
        Fetch permit signals for a location.
        
        Queries permits within radius of location for 3m/6m/12m windows.
        """
        as_of = as_of or datetime.utcnow()
        data_gaps = []
        evidence_refs = []
        
        if not (lat and lon) and not address:
            data_gaps.append("No location provided (lat/lon or address required)")
            return self.create_output(
                signals=self._empty_signals(),
                evidence_refs=[],
                data_gaps=data_gaps,
            )
        
        # Get location from address if needed
        if not (lat and lon) and address:
            # TODO: Geocode address
            data_gaps.append("Address geocoding not implemented, using area-level query")
        
        try:
            # Query permits for different time windows
            count_3m = self._get_permit_count(lat, lon, 3, as_of, address)
            count_6m = self._get_permit_count(lat, lon, 6, as_of, address)
            count_12m = self._get_permit_count(lat, lon, 12, as_of, address)
            
            # Generate evidence refs
            ref_3m = self.generate_evidence_ref("perm")
            ref_6m = self.generate_evidence_ref("perm")
            ref_12m = self.generate_evidence_ref("perm")
            evidence_refs.extend([ref_3m, ref_6m, ref_12m])
            
            # Get permit cost data
            cost_data = self._get_permit_costs(lat, lon, 12, as_of, address)
            cost_ref = self.generate_evidence_ref("perm")
            evidence_refs.append(cost_ref)
            
            # Get permit type distribution
            type_dist = self._get_permit_types(lat, lon, 12, as_of, address)
            
            # Compute trend
            trend = self.compute_trend(count_3m, count_6m, count_12m)
            
            signals = {
                "permit_count_3m": count_3m,
                "permit_count_6m": count_6m,
                "permit_count_12m": count_12m,
                "permit_trend": trend,
                "avg_permit_cost_12m": cost_data.get("avg_cost", 0),
                "total_permit_cost_12m": cost_data.get("total_cost", 0),
                "permit_types": type_dist,
                "has_recent_permits": count_3m > 0,
                "evidence_map": {
                    "count_3m": ref_3m,
                    "count_6m": ref_6m,
                    "count_12m": ref_12m,
                    "costs": cost_ref,
                },
            }
            
        except Exception as e:
            logger.error(f"Error fetching permit signals: {e}")
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
        """Return empty signals structure"""
        return {
            "permit_count_3m": 0,
            "permit_count_6m": 0,
            "permit_count_12m": 0,
            "permit_trend": "stable",
            "avg_permit_cost_12m": 0,
            "total_permit_cost_12m": 0,
            "permit_types": [],
            "has_recent_permits": False,
        }
    
    def _get_permit_count(
        self,
        lat: float,
        lon: float,
        months_back: int,
        as_of: datetime,
        address: str = None,
    ) -> int:
        """Get permit count for time window"""
        start_date = as_of - timedelta(days=months_back * 30)
        
        if lat and lon:
            result = self.client.query_spatial(
                dataset_id=self.dataset_id,
                lat=lat,
                lon=lon,
                radius_meters=Config.DEFAULT_SEARCH_RADIUS_METERS,
                point_field="location",
                date_field="filed_date",
                months_back=months_back,
                select="count(*) as count",
                as_of=as_of,
            )
        else:
            # Fallback to address-based query
            where = f"filed_date >= '{start_date.strftime('%Y-%m-%dT%H:%M:%S')}'"
            if address:
                where = f"({where}) AND upper(street_name) LIKE '%{address.upper()}%'"
            
            result = self.client.query(
                self.dataset_id,
                f"$select=count(*) as count&$where={where}",
            )
        
        if result.data and len(result.data) > 0:
            return int(result.data[0].get("count", 0))
        return 0
    
    def _get_permit_costs(
        self,
        lat: float,
        lon: float,
        months_back: int,
        as_of: datetime,
        address: str = None,
    ) -> Dict[str, float]:
        """Get permit cost statistics"""
        start_date = as_of - timedelta(days=months_back * 30)
        
        # Note: estimated_cost is stored as text in the dataset, so we fetch raw values
        # and compute aggregates locally
        try:
            if lat and lon:
                result = self.client.query_spatial(
                    dataset_id=self.dataset_id,
                    lat=lat,
                    lon=lon,
                    radius_meters=Config.DEFAULT_SEARCH_RADIUS_METERS,
                    point_field="location",
                    date_field="filed_date",
                    months_back=months_back,
                    select="estimated_cost",
                    as_of=as_of,
                )
            else:
                where = f"filed_date >= '{start_date.strftime('%Y-%m-%dT%H:%M:%S')}'"
                # Limit to 1000 records for performance and just get sample stats
                result = self.client.query(
                    self.dataset_id,
                    f"$select=estimated_cost&$where={where}&$limit=1000",
                )
            
            # Parse costs and compute averages locally
            costs = []
            for row in result.data:
                try:
                    cost_str = row.get("estimated_cost", "0") or "0"
                    cost = float(cost_str.replace(",", "").replace("$", ""))
                    if cost > 0:
                        costs.append(cost)
                except (ValueError, TypeError):
                    pass
            
            if costs:
                return {
                    "avg_cost": sum(costs) / len(costs),
                    "total_cost": sum(costs),
                }
        except Exception as e:
            logger.warning(f"Error getting permit costs: {e}")
        
        return {"avg_cost": 0, "total_cost": 0}
    
    def _get_permit_types(
        self,
        lat: float,
        lon: float,
        months_back: int,
        as_of: datetime,
        address: str = None,
    ) -> List[Dict[str, Any]]:
        """Get distribution of permit types"""
        start_date = as_of - timedelta(days=months_back * 30)
        
        if lat and lon:
            result = self.client.query_spatial(
                dataset_id=self.dataset_id,
                lat=lat,
                lon=lon,
                radius_meters=Config.DEFAULT_SEARCH_RADIUS_METERS,
                point_field="location",
                date_field="filed_date",
                months_back=months_back,
                select="permit_type, count(*) as count",
                group="permit_type",
                order="count DESC",
                as_of=as_of,
            )
        else:
            where = f"filed_date >= '{start_date.strftime('%Y-%m-%dT%H:%M:%S')}'"
            result = self.client.query(
                self.dataset_id,
                f"$select=permit_type, count(*) as count&$where={where}&$group=permit_type&$order=count DESC&$limit=10",
            )
        
        return [
            {"type": r.get("permit_type"), "count": int(r.get("count", 0))}
            for r in result.data[:10]
        ]
