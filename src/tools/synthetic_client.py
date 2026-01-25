"""
Synthetic Data Client for Local Testing

Mimics SocrataClient but loads data from data/synthetic_evidence.json.
Allows the multi-agent system to run without live API calls.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class SyntheticQueryResult:
    """Mock QueryResult for synthetic data"""
    def __init__(self, data: List[Dict[str, Any]], dataset_id: str):
        self.data = data
        self.dataset_id = dataset_id
        self.pulled_at = datetime.utcnow()
        self.record_count = len(data)

class SyntheticClient:
    """
    Client for loading synthetic evidence data from local storage.
    
    Interface matches the parts of SocrataClient used by data agents.
    """
    
    def __init__(self, synthetic_data_path: Path = None):
        if synthetic_data_path is None:
            # Default path relative to project root
            self.data_path = Path(__file__).parent.parent.parent / "data" / "synthetic_evidence.json"
        else:
            self.data_path = synthetic_data_path
            
        self._data = None
        self._load_data()

    def _load_data(self):
        """Load the synthetic evidence JSON file"""
        try:
            if self.data_path.exists():
                with open(self.data_path, "r") as f:
                    self._data = json.load(f)
                logger.info(f"Loaded synthetic data from {self.data_path}")
            else:
                logger.warning(f"Synthetic data file not found at {self.data_path}")
                self._data = {}
        except Exception as e:
            logger.error(f"Failed to load synthetic data: {e}")
            self._data = {}

    def query(self, dataset_id: str, soql: str = "", **kwargs) -> SyntheticQueryResult:
        """
        Mock query interface. 
        Note: This is a simplified version that primarily handles business_id filtering.
        """
        # Mapping dataset IDs to synthetic data keys
        mapping = {
            "g8m3-pdis": "businesses",       # Business Registry
            "i98e-djp9": "permits",          # Building Permits
            "nhtv-bhqe": "violations",       # Code Enforcement / DBI Complaints
            "vw6y-z8j6": "complaints_311",    # 311 Complaints
            "wg3w-h783": "sfpd_incidents",   # SFPD Incidents
            "gm2e-bten": "evictions",        # Evictions (mocked as empty or similar)
            "rzkk-54yv": "vacancy"           # Vacancy (mocked)
        }
        
        data_key = mapping.get(dataset_id)
        if not data_key:
            logger.warning(f"No synthetic data mapping for dataset {dataset_id}")
            return SyntheticQueryResult([], dataset_id)
            
        records = self._data.get(data_key)
        if records is None:
            # Fallback to permits or incidents if key missing (some datasets might share structure)
            records = []
            
        import re
        matches = []
        
        # 1. Check for specific ID filters
        id_match = re.search(r"(?:uniqueid|id|business_account_number|business_id)\s*=\s*'([^']+)'", soql, re.IGNORECASE)
        
        # 2. Check for name filters
        name_match = re.search(r"(?:dba_name|ownership_name)\)?\s+like\s+'%([^%]+)%'", soql, re.IGNORECASE)
        
        # 3. Check for address filters
        # Agents use: full_business_address, address, street_name, intersection
        addr_match = re.search(r"(?:full_business_address|address|street_name|intersection)\)?\s+like\s+'%([^%]+)%'", soql, re.IGNORECASE)
        
        if id_match:
            target_id = id_match.group(1)
            matches = [r for r in records if str(r.get("business_id")) == str(target_id) or str(r.get("business_account_number")) == str(target_id) or str(r.get("uniqueid")) == str(target_id)]
        elif name_match:
            term = name_match.group(1).upper()
            matches = [r for r in records if term in (r.get("dba_name") or "").upper() or term in (r.get("ownership_name") or "").upper() or term in (r.get("business_name") or "").upper()]
        elif addr_match:
            term = addr_match.group(1).upper()
            matches = [r for r in records if term in (r.get("address") or "").upper()]
        else:
            # Fallback
            matches = records[:100]
            
        # Special handling for count(*)
        if "count(*)" in soql.lower():
            return SyntheticQueryResult([{"count": len(matches)}], dataset_id)
            
        return SyntheticQueryResult(matches, dataset_id)

    def query_spatial(self, dataset_id: str, lat: float, lon: float, **kwargs) -> SyntheticQueryResult:
        """Mock spatial query interface"""
        # For simplicity, if we query spatially, we return records near that location 
        # or just the records for the same dataset.
        return self.query(dataset_id, **kwargs)

    def query_time_window(self, dataset_id: str, **kwargs) -> SyntheticQueryResult:
        """Mock time window query interface"""
        return self.query(dataset_id, **kwargs)
