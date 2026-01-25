"""
311 Complaints Agent

Fetches 311 case data from SF 311 Cases dataset.
Provides complaint activity signals for risk assessment.

Dataset: vw6y-z8j6 (311 Cases)
Note: Updates nightly ~6am Pacific
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


class Complaints311Agent(BaseDataAgent):
    """
    Agent for querying SF 311 Cases data.
    
    Returns complaint signals:
    - 311_count_3m/6m/12m: Time-windowed complaint counts
    - top_categories: Most common complaint types
    - trend: Direction of complaint activity
    - open_closed_ratio: Ratio of open to closed cases
    """
    
    VERSION = "0.1"
    
    # Complaint categories relevant to business risk
    BUSINESS_RELEVANT_CATEGORIES = [
        "Homeless Concerns",
        "Street and Sidewalk Cleaning",
        "Graffiti",
        "Noise Report",
        "Illegal Dumping",
        "Encampment",
        "Damaged Property",
        "Abandoned Vehicle",
        "Streetlight",
    ]
    
    @property
    def name(self) -> str:
        return "Complaints311Agent"
    
    @property
    def dataset_id(self) -> str:
        return Config.COMPLAINTS_DATASET
    
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
        Fetch 311 complaint signals for a location.
        
        Queries cases within radius for 3m/6m/12m windows.
        """
        as_of = as_of or datetime.utcnow()
        data_gaps = []
        evidence_refs = []
        
        if not (lat and lon) and not address and not neighborhood:
            data_gaps.append("No location provided")
            return self.create_output(
                signals=self._empty_signals(),
                evidence_refs=[],
                data_gaps=data_gaps,
            )
        
        try:
            # Query complaints for different time windows
            count_3m = self._get_complaint_count(lat, lon, 3, as_of, neighborhood)
            count_6m = self._get_complaint_count(lat, lon, 6, as_of, neighborhood)
            count_12m = self._get_complaint_count(lat, lon, 12, as_of, neighborhood)
            
            # Generate evidence refs
            ref_3m = self.generate_evidence_ref("311")
            ref_6m = self.generate_evidence_ref("311")
            ref_12m = self.generate_evidence_ref("311")
            evidence_refs.extend([ref_3m, ref_6m, ref_12m])
            
            # Get category distribution
            categories = self._get_category_distribution(lat, lon, 6, as_of, neighborhood)
            cat_ref = self.generate_evidence_ref("311")
            evidence_refs.append(cat_ref)
            
            # Get status distribution
            status_data = self._get_status_distribution(lat, lon, 6, as_of, neighborhood)
            
            # Compute trend
            trend = self.compute_trend(count_3m, count_6m, count_12m)
            
            # Calculate business-relevant subset
            biz_relevant_count = self._get_business_relevant_count(lat, lon, 6, as_of, neighborhood)
            
            signals = {
                "complaint_count_3m": count_3m,
                "complaint_count_6m": count_6m,
                "complaint_count_12m": count_12m,
                "complaint_trend": trend,
                "top_categories": categories[:5],
                "open_cases": status_data.get("open", 0),
                "closed_cases": status_data.get("closed", 0),
                "open_closed_ratio": self._safe_ratio(
                    status_data.get("open", 0),
                    status_data.get("closed", 1)
                ),
                "business_relevant_count_6m": biz_relevant_count,
                "has_recent_complaints": count_3m > 0,
                "evidence_map": {
                    "count_3m": ref_3m,
                    "count_6m": ref_6m,
                    "count_12m": ref_12m,
                    "categories": cat_ref,
                },
            }
            
        except Exception as e:
            logger.error(f"Error fetching 311 signals: {e}")
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
            "complaint_count_3m": 0,
            "complaint_count_6m": 0,
            "complaint_count_12m": 0,
            "complaint_trend": "stable",
            "top_categories": [],
            "open_cases": 0,
            "closed_cases": 0,
            "open_closed_ratio": 0,
            "business_relevant_count_6m": 0,
            "has_recent_complaints": False,
        }
    
    def _safe_ratio(self, numerator: int, denominator: int) -> float:
        if denominator == 0:
            return 0.0
        return round(numerator / denominator, 2)
    
    def _get_complaint_count(
        self,
        lat: float,
        lon: float,
        months_back: int,
        as_of: datetime,
        neighborhood: str = None,
    ) -> int:
        """Get complaint count for time window"""
        start_date = as_of - timedelta(days=months_back * 30)
        
        if lat and lon:
            result = self.client.query_spatial(
                dataset_id=self.dataset_id,
                lat=lat,
                lon=lon,
                radius_meters=Config.DEFAULT_SEARCH_RADIUS_METERS,
                point_field="point",
                date_field="requested_datetime",
                months_back=months_back,
                select="count(*) as count",
                as_of=as_of,
            )
        elif neighborhood:
            where = f"requested_datetime >= '{start_date.strftime('%Y-%m-%dT%H:%M:%S')}' AND neighborhoods_sffind_boundaries = '{neighborhood}'"
            result = self.client.query(
                self.dataset_id,
                f"$select=count(*) as count&$where={where}",
            )
        else:
            return 0
        
        if result.data and len(result.data) > 0:
            return int(result.data[0].get("count", 0))
        return 0
    
    def _get_category_distribution(
        self,
        lat: float,
        lon: float,
        months_back: int,
        as_of: datetime,
        neighborhood: str = None,
    ) -> List[Dict[str, Any]]:
        """Get distribution of complaint categories"""
        start_date = as_of - timedelta(days=months_back * 30)
        
        if lat and lon:
            result = self.client.query_spatial(
                dataset_id=self.dataset_id,
                lat=lat,
                lon=lon,
                radius_meters=Config.DEFAULT_SEARCH_RADIUS_METERS,
                point_field="point",
                date_field="requested_datetime",
                months_back=months_back,
                select="service_name, count(*) as count",
                group="service_name",
                order="count DESC",
                as_of=as_of,
            )
        elif neighborhood:
            where = f"requested_datetime >= '{start_date.strftime('%Y-%m-%dT%H:%M:%S')}' AND neighborhoods_sffind_boundaries = '{neighborhood}'"
            result = self.client.query(
                self.dataset_id,
                f"$select=service_name, count(*) as count&$where={where}&$group=service_name&$order=count DESC&$limit=10",
            )
        else:
            return []
        
        return [
            {"category": r.get("service_name"), "count": int(r.get("count", 0))}
            for r in result.data[:10]
        ]
    
    def _get_status_distribution(
        self,
        lat: float,
        lon: float,
        months_back: int,
        as_of: datetime,
        neighborhood: str = None,
    ) -> Dict[str, int]:
        """Get open/closed status counts"""
        start_date = as_of - timedelta(days=months_back * 30)
        
        if lat and lon:
            result = self.client.query_spatial(
                dataset_id=self.dataset_id,
                lat=lat,
                lon=lon,
                radius_meters=Config.DEFAULT_SEARCH_RADIUS_METERS,
                point_field="point",
                date_field="requested_datetime",
                months_back=months_back,
                select="status_description, count(*) as count",
                group="status_description",
                as_of=as_of,
            )
        elif neighborhood:
            where = f"requested_datetime >= '{start_date.strftime('%Y-%m-%dT%H:%M:%S')}' AND neighborhoods_sffind_boundaries = '{neighborhood}'"
            result = self.client.query(
                self.dataset_id,
                f"$select=status_description, count(*) as count&$where={where}&$group=status_description",
            )
        else:
            return {"open": 0, "closed": 0}
        
        status_counts = {"open": 0, "closed": 0}
        for r in result.data:
            status = r.get("status_description", "").lower()
            count = int(r.get("count", 0))
            if "open" in status:
                status_counts["open"] += count
            elif "closed" in status:
                status_counts["closed"] += count
        
        return status_counts
    
    def _get_business_relevant_count(
        self,
        lat: float,
        lon: float,
        months_back: int,
        as_of: datetime,
        neighborhood: str = None,
    ) -> int:
        """Get count of business-relevant complaint categories"""
        start_date = as_of - timedelta(days=months_back * 30)
        
        # Build category filter
        cat_filter = " OR ".join([f"service_name = '{cat}'" for cat in self.BUSINESS_RELEVANT_CATEGORIES])
        
        if lat and lon:
            result = self.client.query_spatial(
                dataset_id=self.dataset_id,
                lat=lat,
                lon=lon,
                radius_meters=Config.DEFAULT_SEARCH_RADIUS_METERS,
                point_field="point",
                date_field="requested_datetime",
                months_back=months_back,
                select="count(*) as count",
                where=cat_filter,
                as_of=as_of,
            )
        elif neighborhood:
            where = f"requested_datetime >= '{start_date.strftime('%Y-%m-%dT%H:%M:%S')}' AND neighborhoods_sffind_boundaries = '{neighborhood}' AND ({cat_filter})"
            result = self.client.query(
                self.dataset_id,
                f"$select=count(*) as count&$where={where}",
            )
        else:
            return 0
        
        if result.data and len(result.data) > 0:
            return int(result.data[0].get("count", 0))
        return 0
