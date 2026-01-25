"""
SFPD Incidents Agent

Fetches police incident data from SFPD Incident Reports dataset.
Provides public safety signals for risk assessment.

Dataset: wg3w-h783 (SFPD Incident Reports 2018-present)
Note: Records may be removed for court orders/admin reasons - treat as mutable
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


class SFPDIncidentsAgent(BaseDataAgent):
    """
    Agent for querying SFPD Incident Reports.
    
    Returns public safety signals:
    - incident_count_3m/6m/12m: Time-windowed incident counts
    - incident_categories: Distribution of incident types
    - trend: Direction of incident activity
    
    IMPORTANT: SFPD data is mutable - records can be removed for legal reasons.
    Always track pull_timestamp for audit purposes.
    """
    
    VERSION = "0.1"
    
    # Categories particularly relevant to business risk
    BUSINESS_RELEVANT_CATEGORIES = [
        "Larceny Theft",
        "Burglary",
        "Vandalism",
        "Robbery",
        "Motor Vehicle Theft",
        "Assault",
        "Drug Offense",
        "Disorderly Conduct",
    ]
    
    @property
    def name(self) -> str:
        return "SFPDIncidentsAgent"
    
    @property
    def dataset_id(self) -> str:
        return Config.SFPD_INCIDENTS_DATASET
    
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
        Fetch SFPD incident signals for a location.
        
        Tracks pull_timestamp for audit (data is mutable).
        """
        as_of = as_of or datetime.utcnow()
        pull_timestamp = datetime.utcnow()
        data_gaps = []
        evidence_refs = []
        
        if not (lat and lon) and not neighborhood:
            data_gaps.append("No location or neighborhood provided")
            return self.create_output(
                signals=self._empty_signals(pull_timestamp),
                evidence_refs=[],
                data_gaps=data_gaps,
            )
        
        try:
            # Query incidents for different time windows
            count_3m = self._get_incident_count(lat, lon, 3, as_of, neighborhood)
            count_6m = self._get_incident_count(lat, lon, 6, as_of, neighborhood)
            count_12m = self._get_incident_count(lat, lon, 12, as_of, neighborhood)
            
            # Generate evidence refs
            ref_3m = self.generate_evidence_ref("sfpd")
            ref_6m = self.generate_evidence_ref("sfpd")
            ref_12m = self.generate_evidence_ref("sfpd")
            evidence_refs.extend([ref_3m, ref_6m, ref_12m])
            
            # Get category distribution
            categories = self._get_category_distribution(lat, lon, 6, as_of, neighborhood)
            cat_ref = self.generate_evidence_ref("sfpd")
            evidence_refs.append(cat_ref)
            
            # Get business-relevant count
            biz_count = self._get_business_relevant_count(lat, lon, 6, as_of, neighborhood)
            
            # Compute trend
            trend = self.compute_trend(count_3m, count_6m, count_12m)
            
            signals = {
                "incident_count_3m": count_3m,
                "incident_count_6m": count_6m,
                "incident_count_12m": count_12m,
                "incident_trend": trend,
                "incident_categories": categories[:5],
                "business_relevant_count_6m": biz_count,
                "has_recent_incidents": count_3m > 0,
                "pull_timestamp": pull_timestamp.isoformat(),
                "data_mutable_warning": "SFPD data may be modified/removed for legal reasons",
                "evidence_map": {
                    "count_3m": ref_3m,
                    "count_6m": ref_6m,
                    "count_12m": ref_12m,
                    "categories": cat_ref,
                },
            }
            
        except Exception as e:
            logger.error(f"Error fetching SFPD signals: {e}")
            data_gaps.append(f"Query error: {str(e)}")
            return self.create_output(
                signals=self._empty_signals(pull_timestamp),
                evidence_refs=[],
                data_gaps=data_gaps,
            )
        
        return self.create_output(
            signals=signals,
            evidence_refs=evidence_refs,
            data_gaps=data_gaps,
        )
    
    def _empty_signals(self, pull_timestamp: datetime) -> Dict[str, Any]:
        return {
            "incident_count_3m": 0,
            "incident_count_6m": 0,
            "incident_count_12m": 0,
            "incident_trend": "stable",
            "incident_categories": [],
            "business_relevant_count_6m": 0,
            "has_recent_incidents": False,
            "pull_timestamp": pull_timestamp.isoformat(),
            "data_mutable_warning": "SFPD data may be modified/removed for legal reasons",
        }
    
    def _get_incident_count(
        self,
        lat: float,
        lon: float,
        months_back: int,
        as_of: datetime,
        neighborhood: str = None,
    ) -> int:
        """Get incident count for time window"""
        start_date = as_of - timedelta(days=months_back * 30)
        
        if lat and lon:
            result = self.client.query_spatial(
                dataset_id=self.dataset_id,
                lat=lat,
                lon=lon,
                radius_meters=Config.DEFAULT_SEARCH_RADIUS_METERS,
                point_field="point",
                date_field="incident_date",
                months_back=months_back,
                select="count(*) as count",
                as_of=as_of,
            )
        elif neighborhood:
            where = f"incident_date >= '{start_date.strftime('%Y-%m-%dT%H:%M:%S')}' AND analysis_neighborhood = '{neighborhood}'"
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
        """Get distribution of incident categories"""
        start_date = as_of - timedelta(days=months_back * 30)
        
        if lat and lon:
            result = self.client.query_spatial(
                dataset_id=self.dataset_id,
                lat=lat,
                lon=lon,
                radius_meters=Config.DEFAULT_SEARCH_RADIUS_METERS,
                point_field="point",
                date_field="incident_date",
                months_back=months_back,
                select="incident_category, count(*) as count",
                group="incident_category",
                order="count DESC",
                as_of=as_of,
            )
        elif neighborhood:
            where = f"incident_date >= '{start_date.strftime('%Y-%m-%dT%H:%M:%S')}' AND analysis_neighborhood = '{neighborhood}'"
            result = self.client.query(
                self.dataset_id,
                f"$select=incident_category, count(*) as count&$where={where}&$group=incident_category&$order=count DESC&$limit=10",
            )
        else:
            return []
        
        return [
            {"category": r.get("incident_category"), "count": int(r.get("count", 0))}
            for r in result.data[:10]
        ]
    
    def _get_business_relevant_count(
        self,
        lat: float,
        lon: float,
        months_back: int,
        as_of: datetime,
        neighborhood: str = None,
    ) -> int:
        """Get count of business-relevant incident categories"""
        start_date = as_of - timedelta(days=months_back * 30)
        
        # Build category filter
        cat_filter = " OR ".join([f"incident_category = '{cat}'" for cat in self.BUSINESS_RELEVANT_CATEGORIES])
        
        if lat and lon:
            result = self.client.query_spatial(
                dataset_id=self.dataset_id,
                lat=lat,
                lon=lon,
                radius_meters=Config.DEFAULT_SEARCH_RADIUS_METERS,
                point_field="point",
                date_field="incident_date",
                months_back=months_back,
                select="count(*) as count",
                where=cat_filter,
                as_of=as_of,
            )
        elif neighborhood:
            where = f"incident_date >= '{start_date.strftime('%Y-%m-%dT%H:%M:%S')}' AND analysis_neighborhood = '{neighborhood}' AND ({cat_filter})"
            result = self.client.query(
                self.dataset_id,
                f"$select=count(*) as count&$where={where}",
            )
        else:
            return 0
        
        if result.data and len(result.data) > 0:
            return int(result.data[0].get("count", 0))
        return 0
