"""
Business Registry Agent

Fetches business registration data from SF Registered Business Locations dataset.
Provides canonical business records, locations, and key dates.

Dataset: g8m3-pdis (Registered Business Locations - San Francisco)
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base_agent import BaseDataAgent, AgentOutput

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.config import Config

logger = logging.getLogger(__name__)


class BusinessRegistryAgent(BaseDataAgent):
    """
    Agent for querying SF Registered Business Locations.
    
    Returns canonical business records including:
    - Business name and DBA
    - Address and location
    - Registration dates
    - NAIC codes (industry classification)
    - Active status
    """
    
    VERSION = "0.1"
    
    @property
    def name(self) -> str:
        return "BusinessRegistryAgent"
    
    @property
    def dataset_id(self) -> str:
        return Config.BUSINESS_LICENSE_DATASET
    
    def fetch_signals(
        self,
        entity_id: str = None,
        address: str = None,
        lat: float = None,
        lon: float = None,
        neighborhood: str = None,
        as_of: datetime = None,
        horizon_months: int = 6,
        business_name: str = None,
    ) -> AgentOutput:
        """
        Fetch business registry data.
        
        Searches by business name, address, or location.
        """
        as_of = as_of or datetime.utcnow()
        data_gaps = []
        evidence_refs = []
        
        # Build query based on available identifiers
        results = []
        
        if business_name:
            results = self._search_by_name(business_name)
        elif address:
            results = self._search_by_address(address)
        elif lat and lon:
            results = self._search_by_location(lat, lon)
        else:
            data_gaps.append("No search criteria provided (name, address, or location)")
            return self.create_output(
                signals={"candidates": [], "primary": None},
                evidence_refs=[],
                data_gaps=data_gaps,
            )
        
        # Process results
        candidates = []
        for record in results[:10]:  # Limit to top 10 candidates
            ref = self.generate_evidence_ref("biz")
            evidence_refs.append(ref)
            
            candidate = self._parse_business_record(record)
            candidate["evidence_ref"] = ref
            candidates.append(candidate)
        
        # Score and rank candidates based on match quality
        search_term = (business_name or address or "").upper()
        candidates = self._rank_candidates(candidates, search_term)
        
        # Select primary candidate (best match)
        primary = candidates[0] if candidates else None
        
        signals = {
            "candidates": candidates,
            "primary": primary,
            "total_matches": len(results),
        }
        
        if not candidates:
            data_gaps.append(f"No business records found for query")
        
        return self.create_output(
            signals=signals,
            evidence_refs=evidence_refs,
            data_gaps=data_gaps,
        )
    
    def _search_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Search by business name or DBA"""
        import re
        
        # Extract potential address from the query (e.g., "SONA Fashions, 966 Grant Ave")
        # Handle both comma-separated and space-separated formats
        parts = name.split(',')
        business_name = parts[0].strip().upper()
        address_part = parts[1].strip().upper() if len(parts) > 1 else None
        
        # If no comma, try to detect address in the query (e.g., "SONA Fashions 966 Grant Ave")
        # Look for pattern: number followed by words (street name)
        if not address_part:
            addr_match = re.search(r'(\d+\s+\w+(?:\s+\w+)?(?:\s+(?:st|ave|blvd|rd|dr|way|ct|ln|pl))?)', name, re.IGNORECASE)
            if addr_match:
                address_part = addr_match.group(1).upper()
                # Remove address from business name
                business_name = re.sub(r'\d+\s+\w+(?:\s+\w+)?(?:\s+(?:st|ave|blvd|rd|dr|way|ct|ln|pl))?', '', name, flags=re.IGNORECASE).strip().upper()
        
        # Try to extract street number for more precise matching
        street_num_match = re.search(r'\b(\d+)\b', address_part or name)
        street_num = street_num_match.group(1) if street_num_match else None
        
        # Extract first meaningful word from business name for search
        name_words = [w for w in business_name.split() if len(w) >= 3]
        first_word = name_words[0] if name_words else ''
        
        results = []
        
        # Strategy 1: Search by street number AND city (most precise)
        if street_num and address_part:
            soql = f"""$where=full_business_address like '%{street_num}%' AND city='San Francisco'&$order=location_start_date DESC&$limit=50"""
            try:
                result = self.client.query(self.dataset_id, soql, use_cache=False)
                # Filter for matches that look like our business
                for r in result.data:
                    addr = (r.get('full_business_address') or '').upper()
                    dba = (r.get('dba_name') or '').upper()
                    owner = (r.get('ownership_name') or '').upper()
                    # Check if address matches and name is similar
                    if street_num in addr:
                        # Score by name similarity
                        name_words = set(business_name.replace(',', ' ').split())
                        dba_words = set(dba.replace(',', ' ').split())
                        owner_words = set(owner.replace(',', ' ').split())
                        if name_words & dba_words or name_words & owner_words:
                            results.append(r)
                        elif not results:  # Keep as fallback
                            results.append(r)
            except Exception as e:
                logger.warning(f"Address search failed: {e}")
        
        # Strategy 2: Search by business name directly (case-insensitive)
        if not results:
            # Use first word of business name for LIKE search
            first_word = business_name.split()[0] if business_name else ''
            if first_word and len(first_word) >= 3:
                # Use upper() for case-insensitive search
                soql = f"""$where=upper(dba_name) like '%{first_word.upper()}%' AND city='San Francisco'&$order=location_start_date DESC&$limit=30"""
                try:
                    result = self.client.query(self.dataset_id, soql, use_cache=False)
                    results.extend(result.data)
                except Exception as e:
                    logger.warning(f"Name search failed: {e}")
                    
        # Strategy 3: Also search ownership_name if no results
        if not results:
            first_word = business_name.split()[0] if business_name else ''
            if first_word and len(first_word) >= 3:
                soql = f"""$where=upper(ownership_name) like '%{first_word.upper()}%' AND city='San Francisco'&$order=location_start_date DESC&$limit=30"""
                try:
                    result = self.client.query(self.dataset_id, soql, use_cache=False)
                    results.extend(result.data)
                except Exception as e:
                    logger.warning(f"Ownership search failed: {e}")
        
        # Filter to only SF businesses and sort by match quality
        sf_results = [r for r in results if (r.get('city') or '').upper() in ('SAN FRANCISCO', 'SF')]
        
        return sf_results if sf_results else results[:10]
    
    def _search_by_address(self, address: str) -> List[Dict[str, Any]]:
        """Search by street address"""
        import re
        
        # Extract street number for more precise matching
        address_clean = address.upper().strip()
        # Remove city/state suffixes
        address_clean = re.sub(r',?\s*(SAN FRANCISCO|SF|CA|CALIFORNIA).*$', '', address_clean, flags=re.IGNORECASE)
        
        street_num_match = re.search(r'\b(\d+)\b', address_clean)
        street_num = street_num_match.group(1) if street_num_match else None
        
        if street_num:
            soql = f"""$where=full_business_address like '%{street_num}%' AND city='San Francisco'&$order=location_start_date DESC&$limit=30"""
        else:
            # Fallback to first word
            words = address_clean.split()
            if words:
                soql = f"""$where=full_business_address like '%{words[0]}%' AND city='San Francisco'&$order=location_start_date DESC&$limit=20"""
            else:
                return []
        
        try:
            result = self.client.query(self.dataset_id, soql, use_cache=False)
            # Filter to only SF
            sf_results = [r for r in result.data if (r.get('city') or '').upper() in ('SAN FRANCISCO', 'SF')]
            return sf_results
        except Exception as e:
            logger.warning(f"Address search failed: {e}")
            return []
    
    def _search_by_location(self, lat: float, lon: float, radius: int = 100) -> List[Dict[str, Any]]:
        """Search by geographic location"""
        result = self.client.query_spatial(
            dataset_id=self.dataset_id,
            lat=lat,
            lon=lon,
            radius_meters=radius,
            point_field="business_location",
            select="*",
            order="location_start_date DESC",
            limit=20,
        )
        return result.data
    
    def _parse_business_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw record into structured business data"""
        # Extract location coordinates if available. Data from Socrata
        # sometimes uses `business_location` with `latitude`/`longitude`
        # keys, other times it's `location` with GeoJSON `coordinates`.
        location = record.get("business_location") or record.get("location") or {}
        lat = None
        lon = None

        if isinstance(location, dict):
            # Case A: business_location: {"latitude": ..., "longitude": ...}
            if "latitude" in location and "longitude" in location:
                lat = location.get("latitude")
                lon = location.get("longitude")
            # Case B: location GeoJSON: {"type": "Point", "coordinates": [lon, lat]}
            elif "coordinates" in location and isinstance(location.get("coordinates"), (list, tuple)):
                coords = location.get("coordinates")
                if len(coords) >= 2:
                    lon, lat = coords[0], coords[1]
        
        # Parse dates
        start_date = record.get("location_start_date")
        end_date = record.get("location_end_date")
        
        # Determine active status
        is_active = end_date is None or end_date == ""
        
        return {
            "business_name": record.get("dba_name") or record.get("ownership_name"),
            "ownership_name": record.get("ownership_name"),
            "dba_name": record.get("dba_name"),
            "address": record.get("full_business_address"),
            "city": record.get("city"),
            "state": record.get("state"),
            "zip": record.get("business_zip"),
            "neighborhood": record.get("neighborhoods_analysis_boundaries"),
            "latitude": float(lat) if lat else None,
            "longitude": float(lon) if lon else None,
            "naic_code": record.get("naic_code"),
            "naic_description": record.get("naic_code_description"),
            "location_start_date": start_date,
            "location_end_date": end_date,
            "is_active": is_active,
            "business_id": record.get("uniqueid") or record.get("ttxid"),
            "parking_tax": record.get("parking_tax") == "Y",
            "transient_tax": record.get("transient_occupancy_tax") == "Y",
            "supervisor_district": record.get("supervisor_district"),
        }
    
    def _rank_candidates(self, candidates: List[Dict[str, Any]], search_term: str) -> List[Dict[str, Any]]:
        """Rank candidates by match quality to the search term"""
        import re
        
        # Parse search term to extract business name and address parts
        parts = search_term.split(',')
        search_name = parts[0].strip().upper() if parts else ''
        search_addr = parts[1].strip().upper() if len(parts) > 1 else ''
        
        # Extract street number from search address
        street_num_match = re.search(r'\b(\d+)\b', search_addr)
        search_street_num = street_num_match.group(1) if street_num_match else None
        
        def score_candidate(c: Dict[str, Any]) -> int:
            score = 0
            
            cand_name = (c.get('business_name') or c.get('dba_name') or '').upper()
            cand_addr = (c.get('address') or '').upper()
            
            # Name match scoring
            name_words = set(search_name.replace(',', ' ').split())
            cand_words = set(cand_name.replace(',', ' ').split())
            
            # Exact name match
            if search_name and search_name in cand_name:
                score += 100
            # Word overlap
            overlap = name_words & cand_words
            score += len(overlap) * 20
            
            # Address match scoring
            if search_street_num:
                # Exact street number match (not just contains)
                addr_num_match = re.search(r'\b(\d+)\b', cand_addr)
                if addr_num_match and addr_num_match.group(1) == search_street_num:
                    score += 50
                elif search_street_num in cand_addr:
                    score += 10  # Partial match (e.g., 966 in 2966)
            
            # Street name match
            if search_addr:
                # Extract street name words (skip numbers, city, state)
                search_street_words = [w for w in search_addr.split() if not w.isdigit() and w not in ('SF', 'CA', 'SAN', 'FRANCISCO')]
                for sw in search_street_words:
                    if sw in cand_addr:
                        score += 15
            
            # Active business bonus
            if c.get('is_active'):
                score += 5
            
            # Has coordinates bonus
            if c.get('latitude') and c.get('longitude'):
                score += 3
            
            return score
        
        # Sort by score descending
        scored = [(score_candidate(c), c) for c in candidates]
        scored.sort(key=lambda x: -x[0])
        
        # Add match score to candidates for debugging
        for score, c in scored:
            c['match_score'] = score
        
        return [c for _, c in scored]
    
    def get_business_by_id(self, business_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a specific business by ID"""
        soql = f"$where=uniqueid='{business_id}' OR ttxid='{business_id}'"
        result = self.client.query(self.dataset_id, soql)
        
        if result.data:
            return self._parse_business_record(result.data[0])
        return None
    
    def get_businesses_in_neighborhood(
        self,
        neighborhood: str,
        active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Get all businesses in a neighborhood"""
        where = f"neighborhoods_analysis_boundaries='{neighborhood}'"
        if active_only:
            where = f"({where}) AND location_end_date IS NULL"
        
        soql = f"$where={where}&$limit=1000"
        result = self.client.query(self.dataset_id, soql)
        
        return [self._parse_business_record(r) for r in result.data]
