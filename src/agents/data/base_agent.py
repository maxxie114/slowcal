"""
Base class for all data acquisition agents

Provides common functionality for:
- SoQL query execution
- Evidence ref generation
- Freshness tracking
- Signal output formatting
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import hashlib

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from tools.socrata_client import SocrataClient, QueryResult
from utils.config import Config

logger = logging.getLogger(__name__)


@dataclass
class AgentOutput:
    """Standard output from a data agent"""
    signals: Dict[str, Any]
    evidence_refs: List[str]
    data_gaps: List[str] = field(default_factory=list)
    freshness: Optional[datetime] = None
    pulled_at: datetime = field(default_factory=datetime.utcnow)
    dataset_id: str = ""
    agent_name: str = ""
    agent_version: str = "0.1"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "signals": self.signals,
            "evidence_refs": self.evidence_refs,
            "data_gaps": self.data_gaps,
            "freshness": self.freshness.isoformat() if self.freshness else None,
            "pulled_at": self.pulled_at.isoformat(),
            "dataset_id": self.dataset_id,
            "agent_name": self.agent_name,
            "agent_version": self.agent_version,
        }


class BaseDataAgent(ABC):
    """
    Base class for all data acquisition agents.
    
    Subclasses must implement:
    - fetch_signals(): Query the dataset and return structured signals
    - get_dataset_id(): Return the Socrata dataset ID
    """
    
    VERSION = "0.1"
    
    def __init__(self, socrata_client: SocrataClient = None):
        self.client = socrata_client or SocrataClient()
        self._evidence_counter = 0
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name for logging and audit"""
        pass
    
    @property
    @abstractmethod
    def dataset_id(self) -> str:
        """Socrata dataset ID"""
        pass
    
    @abstractmethod
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
        Fetch signals from the dataset.
        
        Args:
            entity_id: Internal entity ID (if known)
            address: Business address
            lat: Latitude (for spatial queries)
            lon: Longitude (for spatial queries)
            neighborhood: Neighborhood name (for area-level queries)
            as_of: Reference date for time filtering
            horizon_months: Lookback window
        
        Returns:
            AgentOutput with signals, evidence refs, and metadata
        """
        pass
    
    def generate_evidence_ref(self, prefix: str = None) -> str:
        """Generate unique evidence reference ID"""
        self._evidence_counter += 1
        prefix = prefix or self.name.lower().replace(" ", "_")[:10]
        return f"e:{prefix}-{self._evidence_counter:03d}"
    
    def generate_evidence_refs_batch(self, count: int, prefix: str = None) -> List[str]:
        """Generate multiple evidence refs"""
        return [self.generate_evidence_ref(prefix) for _ in range(count)]
    
    def compute_trend(
        self,
        count_3m: int,
        count_6m: int,
        count_12m: int = None,
    ) -> str:
        """
        Compute trend direction from time-windowed counts.
        
        Returns: 'up', 'down', or 'stable'
        """
        if count_6m == 0:
            return "stable"
        
        # Compare recent (3m) vs older period
        recent_rate = count_3m / 3  # monthly average
        older_rate = (count_6m - count_3m) / 3  # previous 3m average
        
        if older_rate == 0:
            return "up" if count_3m > 0 else "stable"
        
        change_pct = (recent_rate - older_rate) / older_rate
        
        if change_pct > 0.1:
            return "up"
        elif change_pct < -0.1:
            return "down"
        else:
            return "stable"
    
    def query_by_location(
        self,
        lat: float,
        lon: float,
        months_back: int,
        select: str = "*",
        group: str = "",
        point_field: str = "point",
        date_field: str = None,
        radius_meters: int = None,
        as_of: datetime = None,
    ) -> QueryResult:
        """Helper to query by location with time filter"""
        radius = radius_meters or Config.DEFAULT_SEARCH_RADIUS_METERS
        
        return self.client.query_spatial(
            dataset_id=self.dataset_id,
            lat=lat,
            lon=lon,
            radius_meters=radius,
            point_field=point_field,
            date_field=date_field,
            months_back=months_back if date_field else None,
            select=select,
            group=group,
            as_of=as_of,
        )
    
    def query_by_address(
        self,
        address: str,
        months_back: int = None,
        date_field: str = None,
        select: str = "*",
        as_of: datetime = None,
    ) -> QueryResult:
        """Helper to query by address match"""
        # Normalize address for matching
        normalized = address.upper().strip()
        
        where = f"upper(address) LIKE '%{normalized}%'"
        
        if date_field and months_back:
            from datetime import timedelta
            as_of = as_of or datetime.utcnow()
            start_date = as_of - timedelta(days=months_back * 30)
            where = f"({where}) AND {date_field} >= '{start_date.strftime('%Y-%m-%dT%H:%M:%S')}'"
        
        soql = f"$select={select}&$where={where}"
        return self.client.query(self.dataset_id, soql)
    
    def create_output(
        self,
        signals: Dict[str, Any],
        evidence_refs: List[str],
        data_gaps: List[str] = None,
        query_result: QueryResult = None,
    ) -> AgentOutput:
        """Create standardized agent output"""
        return AgentOutput(
            signals=signals,
            evidence_refs=evidence_refs,
            data_gaps=data_gaps or [],
            freshness=query_result.pulled_at if query_result else datetime.utcnow(),
            pulled_at=datetime.utcnow(),
            dataset_id=self.dataset_id,
            agent_name=self.name,
            agent_version=self.VERSION,
        )
