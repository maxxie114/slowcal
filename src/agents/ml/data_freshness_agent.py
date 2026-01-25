"""
Data Freshness Agent

Monitors data freshness and alerts on stale data.
Compares actual data timestamps against expected update frequencies.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.config import Config

logger = logging.getLogger(__name__)


@dataclass
class FreshnessCheck:
    """Result of freshness check"""
    dataset_key: str
    dataset_id: str
    expected_max_age_hours: int
    actual_age_hours: Optional[float]
    is_fresh: bool
    last_updated: Optional[datetime]
    warning: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_key": self.dataset_key,
            "dataset_id": self.dataset_id,
            "expected_max_age_hours": self.expected_max_age_hours,
            "actual_age_hours": self.actual_age_hours,
            "is_fresh": self.is_fresh,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "warning": self.warning,
        }


@dataclass
class FreshnessReport:
    """Complete freshness report for all datasets"""
    check_time: datetime
    all_fresh: bool
    checks: List[FreshnessCheck]
    warnings: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_time": self.check_time.isoformat(),
            "all_fresh": self.all_fresh,
            "checks": [c.to_dict() for c in self.checks],
            "warnings": self.warnings,
        }


class DataFreshnessAgent:
    """
    Agent for monitoring data freshness.
    
    Checks each dataset against expected update frequency
    and warns if data is stale.
    
    Example usage:
        agent = DataFreshnessAgent()
        report = agent.check_all_freshness(
            pulled_timestamps={
                "complaints_311": datetime(2026, 1, 24, 10, 0),
                "permits": datetime(2026, 1, 23, 15, 0),
            }
        )
        
        if not report.all_fresh:
            for warning in report.warnings:
                print(f"⚠️ {warning}")
    """
    
    VERSION = "0.1"
    
    @property
    def name(self) -> str:
        return "DataFreshnessAgent"
    
    def check_freshness(
        self,
        dataset_key: str,
        pulled_at: datetime,
        as_of: datetime = None,
    ) -> FreshnessCheck:
        """
        Check freshness of a single dataset.
        
        Args:
            dataset_key: Key from Config.DATASETS
            pulled_at: When the data was last pulled
            as_of: Reference time (defaults to now)
        
        Returns:
            FreshnessCheck result
        """
        as_of = as_of or datetime.utcnow()
        
        # Get expected freshness threshold
        thresholds = Config.DATA_FRESHNESS_THRESHOLDS
        expected_hours = thresholds.get(dataset_key, 168)  # Default 1 week
        
        # Get dataset info
        dataset_info = Config.DATASETS.get(dataset_key, {})
        dataset_id = dataset_info.get("id", "unknown")
        
        # Calculate age
        age_hours = None
        is_fresh = True
        warning = None
        
        if pulled_at:
            age_delta = as_of - pulled_at
            age_hours = age_delta.total_seconds() / 3600
            
            if age_hours > expected_hours:
                is_fresh = False
                warning = (
                    f"Dataset '{dataset_key}' is stale: "
                    f"{age_hours:.1f}h old (expected <{expected_hours}h)"
                )
        else:
            is_fresh = False
            warning = f"Dataset '{dataset_key}' has no pull timestamp"
        
        return FreshnessCheck(
            dataset_key=dataset_key,
            dataset_id=dataset_id,
            expected_max_age_hours=expected_hours,
            actual_age_hours=round(age_hours, 1) if age_hours else None,
            is_fresh=is_fresh,
            last_updated=pulled_at,
            warning=warning,
        )
    
    def check_all_freshness(
        self,
        pulled_timestamps: Dict[str, datetime],
        as_of: datetime = None,
    ) -> FreshnessReport:
        """
        Check freshness of all datasets.
        
        Args:
            pulled_timestamps: Dict mapping dataset_key to pull timestamp
            as_of: Reference time
        
        Returns:
            FreshnessReport with all checks
        """
        as_of = as_of or datetime.utcnow()
        checks = []
        warnings = []
        
        # Check each dataset with known thresholds
        for dataset_key in Config.DATA_FRESHNESS_THRESHOLDS.keys():
            pulled_at = pulled_timestamps.get(dataset_key)
            check = self.check_freshness(dataset_key, pulled_at, as_of)
            checks.append(check)
            
            if check.warning:
                warnings.append(check.warning)
        
        return FreshnessReport(
            check_time=as_of,
            all_fresh=len(warnings) == 0,
            checks=checks,
            warnings=warnings,
        )
    
    def get_311_freshness_note(self) -> str:
        """
        Get note about 311 data freshness.
        
        311 updates nightly ~6am Pacific.
        """
        return (
            "311 Cases dataset updates nightly around 6:00 AM Pacific Time. "
            "Data from the current day may not yet be available."
        )
    
    def should_refetch(
        self,
        dataset_key: str,
        last_pulled: datetime,
    ) -> bool:
        """
        Determine if a dataset should be refetched.
        
        Args:
            dataset_key: Dataset key
            last_pulled: When data was last pulled
        
        Returns:
            True if data should be refetched
        """
        check = self.check_freshness(dataset_key, last_pulled)
        return not check.is_fresh
    
    def estimate_next_update(
        self,
        dataset_key: str,
        last_known_update: datetime = None,
    ) -> Optional[datetime]:
        """
        Estimate when dataset will next be updated.
        
        Args:
            dataset_key: Dataset key
            last_known_update: Last known update time
        
        Returns:
            Estimated next update time
        """
        dataset_info = Config.DATASETS.get(dataset_key, {})
        frequency = dataset_info.get("update_frequency", "unknown")
        
        if not last_known_update:
            return None
        
        # Estimate based on frequency
        if frequency == "nightly":
            # Next 6am Pacific
            next_day = last_known_update + timedelta(days=1)
            return next_day.replace(hour=6, minute=0, second=0, microsecond=0)
        elif frequency == "daily":
            return last_known_update + timedelta(hours=24)
        elif frequency == "weekly":
            return last_known_update + timedelta(days=7)
        elif frequency == "quarterly":
            return last_known_update + timedelta(days=90)
        else:
            return None
