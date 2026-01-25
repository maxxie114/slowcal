"""
Vacancy Corridor Agent

Fetches commercial vacancy data from SF datasets.
Provides corridor-level economic stress signals.

Uses only rzkk-54yv (Taxable Commercial Spaces) dataset which has:
- latitude/longitude/location_point for spatial queries  
- vacant field (YES/NO) for vacancy status
- analysis_neighborhood for area filtering

Note: iynh-ydf2 (Commercial Vacancy Tax) is skipped - it's a visualization canvas
that doesn't support spatial queries.

IMPORTANT: Do NOT use filer_name field (PII)
"""

import logging
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_agent import BaseDataAgent, AgentOutput

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.config import Config
from tools.socrata_client import SocrataClient

logger = logging.getLogger(__name__)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate haversine distance between two points in km."""
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


class VacancyCorridorAgent(BaseDataAgent):
    """
    Agent for querying commercial vacancy data.
    
    Uses the Taxable Commercial Spaces dataset (rzkk-54yv) which contains:
    - Commercial space locations (latitude, longitude, location_point)
    - Vacancy status (vacant field: YES/NO)
    - Neighborhood info (analysis_neighborhood)
    
    Returns corridor-level economic signals:
    - vacancy_rate: Commercial vacancy rate in corridor
    - vacancy_trend: Direction of vacancy changes
    - corridor_health: Overall commercial corridor health
    
    PRIVACY: Filer names are NOT used in any analysis (PII protection).
    """
    
    VERSION = "0.2"  # Simplified version
    
    @property
    def name(self) -> str:
        return "VacancyCorridorAgent"
    
    @property
    def dataset_id(self) -> str:
        return Config.TAXABLE_COMMERCIAL_SPACES_DATASET  # rzkk-54yv
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._local_data: Optional[List[Dict]] = None
        self._load_local_data()
    
    def _load_local_data(self) -> None:
        """Load local dataset file if available."""
        # Check data/dataset/ folder first
        dataset_dir = Config.DATA_DIR / "dataset"
        local_file = dataset_dir / f"{self.dataset_id}.json"
        
        if local_file.exists():
            try:
                with open(local_file, 'r') as f:
                    self._local_data = json.load(f)
                logger.info(f"Loaded {len(self._local_data)} records from local file: {local_file}")
            except Exception as e:
                logger.warning(f"Failed to load local file {local_file}: {e}")
                self._local_data = None
        else:
            # Try cache dir
            cache_file = Config.RAW_DATA_DIR / "cache" / f"{self.dataset_id}.json"
            if cache_file.exists():
                try:
                    with open(cache_file, 'r') as f:
                        self._local_data = json.load(f)
                    logger.info(f"Loaded {len(self._local_data)} records from cache: {cache_file}")
                except Exception as e:
                    logger.warning(f"Failed to load cache file {cache_file}: {e}")
                    self._local_data = None

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
            # Get all commercial space data with vacancy status
            space_data = self._get_commercial_spaces_with_vacancy(area, lat, lon)
            evidence_ref = self.generate_evidence_ref("vac")
            evidence_refs.append(evidence_ref)
            
            total_spaces = space_data.get("total_spaces", 0)
            vacant_spaces = space_data.get("vacant_count", 0)
            
            vacancy_rate = (vacant_spaces / total_spaces * 100) if total_spaces > 0 else 0
            
            # Determine corridor health
            corridor_health = self._assess_corridor_health(vacancy_rate)
            
            signals = {
                "total_commercial_spaces": total_spaces,
                "vacant_spaces": vacant_spaces,
                "vacancy_rate_pct": round(vacancy_rate, 1),
                "vacancy_trend": "stable",  # Would need historical data
                "corridor_health": corridor_health,
                "avg_space_sqft": space_data.get("avg_sqft", 0),
                "space_types": space_data.get("types", []),
                "has_high_vacancy": vacancy_rate > 10,
                "evidence_map": {
                    "commercial_spaces": evidence_ref,
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
    
    def _assess_corridor_health(self, vacancy_rate: float) -> str:
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
    
    def _get_commercial_spaces_with_vacancy(
        self,
        area: str,
        lat: float,
        lon: float,
        radius_km: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Get commercial space data with vacancy status.
        Uses local file if available, otherwise queries API.
        """
        # If we have local data, filter it directly
        if self._local_data:
            return self._filter_local_data(area, lat, lon, radius_km)
        
        # Otherwise, try API query
        return self._query_api(area, lat, lon, radius_km)
    
    def _filter_local_data(
        self,
        area: str,
        lat: float,
        lon: float,
        radius_km: float,
    ) -> Dict[str, Any]:
        """Filter local dataset by area or location."""
        filtered = []
        
        for record in self._local_data:
            if not isinstance(record, dict):
                continue
            
            # Filter by location if lat/lon provided
            if lat and lon:
                rec_lat = None
                rec_lon = None
                
                # Try direct latitude/longitude fields
                if 'latitude' in record and 'longitude' in record:
                    try:
                        rec_lat = float(record['latitude'])
                        rec_lon = float(record['longitude'])
                    except (ValueError, TypeError):
                        pass
                
                # Try location_point GeoJSON
                if (rec_lat is None or rec_lon is None) and 'location_point' in record:
                    loc = record['location_point']
                    if isinstance(loc, dict) and 'coordinates' in loc:
                        coords = loc['coordinates']
                        if isinstance(coords, list) and len(coords) >= 2:
                            try:
                                rec_lon = float(coords[0])
                                rec_lat = float(coords[1])
                            except (ValueError, TypeError):
                                pass
                
                if rec_lat is not None and rec_lon is not None:
                    distance = _haversine_km(lat, lon, rec_lat, rec_lon)
                    if distance <= radius_km:
                        filtered.append(record)
            
            # Filter by area/neighborhood if no lat/lon
            elif area:
                rec_neighborhood = record.get('analysis_neighborhood', '').upper()
                if area.upper() in rec_neighborhood or rec_neighborhood in area.upper():
                    filtered.append(record)
        
        # Count vacancies
        total = len(filtered)
        vacant_count = sum(
            1 for r in filtered 
            if str(r.get('vacant', '')).upper() in ('YES', 'VACANT', 'TRUE', '1')
        )
        
        return {
            "total_spaces": total,
            "vacant_count": vacant_count,
            "avg_sqft": 0,  # Not available in this dataset
            "types": [],
        }
    
    def _query_api(
        self,
        area: str,
        lat: float,
        lon: float,
        radius_km: float,
    ) -> Dict[str, Any]:
        """Query API for commercial spaces (fallback if no local data)."""
        try:
            if lat and lon:
                # Spatial query using location_point
                result = self.client.query_spatial(
                    dataset_id=self.dataset_id,
                    lat=lat,
                    lon=lon,
                    radius_meters=int(radius_km * 1000),
                    point_field="location_point",
                    select="vacant, latitude, longitude",
                    limit=5000,
                )
            elif area:
                # Area-based query
                from tools.socrata_client import sanitize_for_soql
                safe_area = sanitize_for_soql(area)
                soql = f"$select=vacant, latitude, longitude&$where=analysis_neighborhood = '{safe_area}'&$limit=5000"
                result = self.client.query(self.dataset_id, soql)
            else:
                return {"total_spaces": 0, "vacant_count": 0, "avg_sqft": 0, "types": []}
            
            if result.data:
                total = len(result.data)
                vacant_count = sum(
                    1 for r in result.data 
                    if str(r.get('vacant', '')).upper() in ('YES', 'VACANT', 'TRUE', '1')
                )
                return {
                    "total_spaces": total,
                    "vacant_count": vacant_count,
                    "avg_sqft": 0,
                    "types": [],
                }
        except Exception as e:
            logger.warning(f"API query failed: {e}")
        
        return {"total_spaces": 0, "vacant_count": 0, "avg_sqft": 0, "types": []}
