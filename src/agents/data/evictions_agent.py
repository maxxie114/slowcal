"""
Evictions Agent

Fetches eviction notice data from SF Eviction Notices dataset.
Provides neighborhood economic stress signals.

Dataset: 5cei-gny5 (Eviction Notices)
Note: Historic duplicate row issue (fixed); keep dedupe logic
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from .base_agent import BaseDataAgent, AgentOutput

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.config import Config

logger = logging.getLogger(__name__)


class EvictionsAgent(BaseDataAgent):
    """
    Agent for querying SF Eviction Notices data.
    
    Returns neighborhood economic stress signals:
    - eviction_count_3m/6m/12m: Time-windowed eviction notice counts
    - eviction_rate: Evictions per neighborhood
    - eviction_reasons: Distribution of eviction reasons
    - trend: Direction of eviction activity
    
    NOTE: This dataset had historic duplicate rows. Dedupe logic is maintained.
    """
    
    VERSION = "0.1"
    
    @property
    def name(self) -> str:
        return "EvictionsAgent"
    
    @property
    def dataset_id(self) -> str:
        return Config.EVICTION_NOTICES_DATASET
    
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
        Fetch eviction signals for a neighborhood.
        
        Evictions are analyzed at neighborhood level (not individual address).
        """
        as_of = as_of or datetime.utcnow()
        data_gaps = []
        evidence_refs = []
        
        if not neighborhood:
            data_gaps.append("Neighborhood required for eviction analysis")
            return self.create_output(
                signals=self._empty_signals(),
                evidence_refs=[],
                data_gaps=data_gaps,
            )
        
        try:
            # Query evictions for different time windows
            count_3m = self._get_eviction_count(neighborhood, 3, as_of)
            count_6m = self._get_eviction_count(neighborhood, 6, as_of)
            count_12m = self._get_eviction_count(neighborhood, 12, as_of)
            
            # Generate evidence refs
            ref_3m = self.generate_evidence_ref("evic")
            ref_6m = self.generate_evidence_ref("evic")
            ref_12m = self.generate_evidence_ref("evic")
            evidence_refs.extend([ref_3m, ref_6m, ref_12m])
            
            # Get eviction reasons
            reasons = self._get_eviction_reasons(neighborhood, 12, as_of)
            reason_ref = self.generate_evidence_ref("evic")
            evidence_refs.append(reason_ref)
            
            # Get citywide context for comparison
            citywide_avg = self._get_citywide_average(12, as_of)
            
            # Compute trend
            trend = self.compute_trend(count_3m, count_6m, count_12m)
            
            # Calculate rate relative to citywide
            relative_rate = count_12m / citywide_avg if citywide_avg > 0 else 1.0
            
            signals = {
                "eviction_count_3m": count_3m,
                "eviction_count_6m": count_6m,
                "eviction_count_12m": count_12m,
                "eviction_trend": trend,
                "eviction_reasons": reasons[:5],
                "citywide_avg_12m": citywide_avg,
                "relative_to_citywide": round(relative_rate, 2),
                "neighborhood_stress_level": self._categorize_stress(relative_rate),
                "evidence_map": {
                    "count_3m": ref_3m,
                    "count_6m": ref_6m,
                    "count_12m": ref_12m,
                    "reasons": reason_ref,
                },
            }
            
        except Exception as e:
            logger.error(f"Error fetching eviction signals: {e}")
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
            "eviction_count_3m": 0,
            "eviction_count_6m": 0,
            "eviction_count_12m": 0,
            "eviction_trend": "stable",
            "eviction_reasons": [],
            "citywide_avg_12m": 0,
            "relative_to_citywide": 1.0,
            "neighborhood_stress_level": "unknown",
        }
    
    def _categorize_stress(self, relative_rate: float) -> str:
        """Categorize neighborhood stress based on eviction rate"""
        if relative_rate > 1.5:
            return "high"
        elif relative_rate > 1.0:
            return "moderate"
        elif relative_rate > 0.5:
            return "low"
        else:
            return "very_low"
    
    def _get_eviction_count(
        self,
        neighborhood: str,
        months_back: int,
        as_of: datetime,
    ) -> int:
        """Get deduplicated eviction count for time window"""
        start_date = as_of - timedelta(days=months_back * 30)
        
        where = f"file_date >= '{start_date.strftime('%Y-%m-%dT%H:%M:%S')}' AND neighborhood = '{neighborhood}'"
        
        result = self.client.query(
            self.dataset_id,
            f"$select=eviction_id, address, file_date&$where={where}",
        )
        
        # Dedupe by eviction_id (historic duplicate issue)
        seen_ids: Set[str] = set()
        unique_count = 0
        for r in result.data:
            eviction_id = r.get("eviction_id", "")
            if eviction_id and eviction_id not in seen_ids:
                seen_ids.add(eviction_id)
                unique_count += 1
        
        return unique_count
    
    def _get_eviction_reasons(
        self,
        neighborhood: str,
        months_back: int,
        as_of: datetime,
    ) -> List[Dict[str, Any]]:
        """Get distribution of eviction reasons"""
        start_date = as_of - timedelta(days=months_back * 30)
        
        # Common eviction reason fields in the dataset
        reason_fields = [
            "non_payment", "breach", "nuisance", "illegal_use",
            "owner_move_in", "demolition", "capital_improvement",
            "ellis_act_withdrawal", "condo_conversion", "roommate_same_unit"
        ]
        
        where = f"file_date >= '{start_date.strftime('%Y-%m-%dT%H:%M:%S')}' AND neighborhood = '{neighborhood}'"
        
        # Get all evictions and count reasons
        result = self.client.query(
            self.dataset_id,
            f"$select=*&$where={where}",
        )
        
        reason_counts: Dict[str, int] = {}
        for r in result.data:
            for field in reason_fields:
                if r.get(field) in [True, "true", "True", "1", 1]:
                    reason_counts[field] = reason_counts.get(field, 0) + 1
        
        # Sort by count
        sorted_reasons = sorted(
            reason_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [
            {"reason": reason, "count": count}
            for reason, count in sorted_reasons
        ]
    
    def _get_citywide_average(
        self,
        months_back: int,
        as_of: datetime,
    ) -> float:
        """Get average evictions per neighborhood citywide"""
        start_date = as_of - timedelta(days=months_back * 30)
        
        where = f"file_date >= '{start_date.strftime('%Y-%m-%dT%H:%M:%S')}'"
        
        result = self.client.query(
            self.dataset_id,
            f"$select=neighborhood, count(*) as count&$where={where}&$group=neighborhood",
        )
        
        if not result.data:
            return 0.0
        
        total = sum(int(r.get("count", 0)) for r in result.data)
        num_neighborhoods = len(result.data)
        
        return total / num_neighborhoods if num_neighborhoods > 0 else 0.0
