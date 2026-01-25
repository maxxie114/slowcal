"""
Vacancy Corridor Agent

Fetches commercial vacancy data from SF datasets.
Provides corridor-level economic stress signals.

Datasets:
- rzkk-54yv (Taxable Commercial Spaces)
- iynh-ydf2 (Commercial Vacancy Tax Status)

IMPORTANT: Do NOT use filer_name field from vacancy tax dataset (PII)
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


class VacancyCorridorAgent(BaseDataAgent):
    """
    Agent for querying commercial vacancy data.
    
    Returns corridor-level economic signals:
    - vacancy_rate: Commercial vacancy rate in corridor
    - vacancy_trend: Direction of vacancy changes
    - corridor_health: Overall commercial corridor health
    
    PRIVACY: Filer names are NOT used in any analysis (PII protection).
    """
    
    VERSION = "0.1"
    
    # Use the taxable commercial spaces dataset as primary
    @property
    def name(self) -> str:
        return "VacancyCorridorAgent"
    
    @property
    def dataset_id(self) -> str:
        return Config.TAXABLE_COMMERCIAL_SPACES_DATASET
    
    @property
    def vacancy_tax_dataset_id(self) -> str:
        return Config.COMMERCIAL_VACANCY_TAX_DATASET
    
    def fetch_signals(
        self,
        entity_id: str = None,
        address: str = None,
        lat: float = None,
        lon: float = None,
        neighborhood: str = None,
        as_of: datetime = None,
        horizon_months: int = 6,
        corridor: str = None,
    ) -> AgentOutput:
        """
        Fetch commercial vacancy signals for a corridor/neighborhood.
        """
        as_of = as_of or datetime.utcnow()
        data_gaps = []
        evidence_refs = []
        
        # Use neighborhood if corridor not specified
        area = corridor or neighborhood
        
        if not area and not (lat and lon):
            data_gaps.append("No area (corridor, neighborhood, or location) provided")
            return self.create_output(
                signals=self._empty_signals(),
                evidence_refs=[],
                data_gaps=data_gaps,
            )
        
        try:
            # Get commercial space data
            space_data = self._get_commercial_spaces(area, lat, lon)
            space_ref = self.generate_evidence_ref("vac")
            evidence_refs.append(space_ref)
            
            # Get vacancy tax data
            vacancy_data = self._get_vacancy_status(area, lat, lon)
            vacancy_ref = self.generate_evidence_ref("vac")
            evidence_refs.append(vacancy_ref)
            
            # Calculate vacancy metrics
            total_spaces = space_data.get("total_spaces", 0)
            vacant_spaces = vacancy_data.get("vacant_count", 0)
            
            vacancy_rate = (vacant_spaces / total_spaces * 100) if total_spaces > 0 else 0
            
            # Determine corridor health
            corridor_health = self._assess_corridor_health(vacancy_rate, vacancy_data)
            
            signals = {
                "total_commercial_spaces": total_spaces,
                "vacant_spaces": vacant_spaces,
                "vacancy_rate_pct": round(vacancy_rate, 1),
                "vacancy_trend": vacancy_data.get("trend", "stable"),
                "corridor_health": corridor_health,
                "avg_space_sqft": space_data.get("avg_sqft", 0),
                "space_types": space_data.get("types", []),
                "has_high_vacancy": vacancy_rate > 10,
                "evidence_map": {
                    "commercial_spaces": space_ref,
                    "vacancy_status": vacancy_ref,
                },
                "privacy_note": "Filer/owner names are not used in this analysis",
            }
            
        except Exception as e:
            logger.error(f"Error fetching vacancy signals: {e}")
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
            "total_commercial_spaces": 0,
            "vacant_spaces": 0,
            "vacancy_rate_pct": 0,
            "vacancy_trend": "stable",
            "corridor_health": "unknown",
            "avg_space_sqft": 0,
            "space_types": [],
            "has_high_vacancy": False,
            "privacy_note": "Filer/owner names are not used in this analysis",
        }
    
    def _assess_corridor_health(
        self,
        vacancy_rate: float,
        vacancy_data: Dict[str, Any],
    ) -> str:
        """Assess overall corridor health based on vacancy metrics"""
        if vacancy_rate > 20:
            return "critical"
        elif vacancy_rate > 15:
            return "poor"
        elif vacancy_rate > 10:
            return "moderate"
        elif vacancy_rate > 5:
            return "good"
        else:
            return "excellent"
    
    def _get_commercial_spaces(
        self,
        area: str,
        lat: float,
        lon: float,
    ) -> Dict[str, Any]:
        """Get commercial space inventory data"""
        try:
            if lat and lon:
                result = self.client.query_spatial(
                    dataset_id=self.dataset_id,
                    lat=lat,
                    lon=lon,
                    radius_meters=1000,  # Larger radius for corridor analysis
                    point_field="location",
                    select="count(*) as count, avg(square_feet) as avg_sqft",
                )
            elif area:
                # Query by area/neighborhood
                result = self.client.query(
                    self.dataset_id,
                    f"$select=count(*) as count, avg(square_feet) as avg_sqft&$where=neighborhood = '{area}'",
                )
            else:
                return {"total_spaces": 0, "avg_sqft": 0, "types": []}
            
            if result.data and len(result.data) > 0:
                row = result.data[0]
                return {
                    "total_spaces": int(row.get("count", 0)),
                    "avg_sqft": float(row.get("avg_sqft", 0) or 0),
                    "types": [],  # Would need additional query for type breakdown
                }
        except Exception as e:
            logger.warning(f"Error querying commercial spaces: {e}")
        
        return {"total_spaces": 0, "avg_sqft": 0, "types": []}
    
    def _get_vacancy_status(
        self,
        area: str,
        lat: float,
        lon: float,
    ) -> Dict[str, Any]:
        """Get vacancy tax status data (excluding PII fields)"""
        try:
            # Query vacancy tax status - explicitly exclude filer_name
            # This dataset contains owner/tenant info that we should NOT use
            
            if lat and lon:
                result = self.client.query_spatial(
                    dataset_id=self.vacancy_tax_dataset_id,
                    lat=lat,
                    lon=lon,
                    radius_meters=1000,
                    point_field="location",
                    # Only select non-PII fields
                    select="count(*) as count",
                    where="vacancy_status = 'Vacant'",
                )
            elif area:
                result = self.client.query(
                    self.vacancy_tax_dataset_id,
                    f"$select=count(*) as count&$where=neighborhood = '{area}' AND vacancy_status = 'Vacant'",
                )
            else:
                return {"vacant_count": 0, "trend": "stable"}
            
            if result.data and len(result.data) > 0:
                return {
                    "vacant_count": int(result.data[0].get("count", 0)),
                    "trend": "stable",  # Would need historical data for trend
                }
        except Exception as e:
            logger.warning(f"Error querying vacancy status: {e}")
        
        return {"vacant_count": 0, "trend": "stable"}
