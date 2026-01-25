"""
Entity Resolver Agent

Merges candidates from multiple sources to produce a resolved entity.
Outputs confidence-scored entity resolution with join strategy.
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .address_normalize_agent import AddressNormalizeAgent, NormalizedAddress
from .geo_resolve_agent import GeoResolveAgent, GeoLocation

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.config import Config

logger = logging.getLogger(__name__)


@dataclass
class ResolvedEntity:
    """Fully resolved business entity"""
    entity_id: str
    business_name: str
    address: str
    normalized_address: str
    latitude: Optional[float]
    longitude: Optional[float]
    geohash: Optional[str]
    neighborhood: Optional[str]
    match_confidence: float
    join_strategy: str  # "exact_address", "spatial_radius", "neighborhood_aggregate"
    source_records: List[Dict[str, Any]]
    data_gaps: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "business_name": self.business_name,
            "address": self.address,
            "normalized_address": self.normalized_address,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "geohash": self.geohash,
            "neighborhood": self.neighborhood,
            "match_confidence": self.match_confidence,
            "join_strategy": self.join_strategy,
        }


class EntityResolverAgent:
    """
    Agent for resolving business entities from multiple data sources.
    
    Merges candidates from:
    - Business registry
    - Normalized addresses
    - Geo resolution
    
    Produces:
    - entity_id (internal identifier)
    - match_confidence [0, 1]
    - join_strategy for downstream queries
    
    Example usage:
        agent = EntityResolverAgent()
        entity = agent.resolve(
            business_name="Joe's Coffee",
            address="123 Main St",
            registry_candidates=[...],
        )
        
        if entity.match_confidence < 0.6:
            print("Low confidence - requires user confirmation")
    """
    
    VERSION = "0.1"
    CONFIDENCE_THRESHOLD = Config.ENTITY_MATCH_CONFIDENCE_THRESHOLD
    
    def __init__(self):
        self.address_agent = AddressNormalizeAgent()
        self.geo_agent = GeoResolveAgent()
    
    @property
    def name(self) -> str:
        return "EntityResolverAgent"
    
    def resolve(
        self,
        business_name: str = None,
        address: str = None,
        lat: float = None,
        lon: float = None,
        registry_candidates: List[Dict[str, Any]] = None,
    ) -> ResolvedEntity:
        """
        Resolve a business entity from available information.
        
        Args:
            business_name: Business name to search
            address: Street address
            lat: Latitude (if known)
            lon: Longitude (if known)
            registry_candidates: Candidates from BusinessRegistryAgent
        
        Returns:
            ResolvedEntity with confidence score
        """
        registry_candidates = registry_candidates or []
        data_gaps = []
        
        # Normalize input address
        normalized_addr = None
        if address:
            normalized_addr = self.address_agent.normalize(address)
        
        # Score and rank candidates
        scored_candidates = []
        for candidate in registry_candidates:
            score = self._score_candidate(
                candidate,
                business_name=business_name,
                normalized_address=normalized_addr,
                lat=lat,
                lon=lon,
            )
            scored_candidates.append((candidate, score))
        
        # Sort by score descending
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Select best candidate
        if scored_candidates:
            best_candidate, best_score = scored_candidates[0]
            return self._build_resolved_entity(
                candidate=best_candidate,
                score=best_score,
                normalized_address=normalized_addr,
                source_records=[c for c, _ in scored_candidates[:3]],
                data_gaps=data_gaps,
            )
        
        # No candidates - try to build entity from input
        if address or (lat and lon):
            return self._build_entity_from_input(
                business_name=business_name,
                address=address,
                normalized_address=normalized_addr,
                lat=lat,
                lon=lon,
                data_gaps=data_gaps,
            )
        
        # Cannot resolve
        data_gaps.append("Insufficient information to resolve entity")
        return self._empty_entity(data_gaps)
    
    def _score_candidate(
        self,
        candidate: Dict[str, Any],
        business_name: str = None,
        normalized_address: NormalizedAddress = None,
        lat: float = None,
        lon: float = None,
    ) -> float:
        """
        Score a candidate record against input.
        
        Returns confidence score 0-1.
        """
        score = 0.0
        
        # Name matching (0.4 weight)
        if business_name:
            candidate_name = (
                candidate.get("business_name") or
                candidate.get("dba_name") or
                candidate.get("ownership_name") or ""
            )
            name_score = self._name_similarity(business_name, candidate_name)
            score += 0.4 * name_score
        
        # Address matching (0.4 weight)
        if normalized_address:
            candidate_addr = candidate.get("address", "")
            addr_score = self.address_agent.match_score(
                normalized_address.original,
                candidate_addr,
            )
            score += 0.4 * addr_score
        
        # Location matching (0.2 weight)
        if lat and lon:
            candidate_lat = candidate.get("latitude")
            candidate_lon = candidate.get("longitude")
            if candidate_lat and candidate_lon:
                distance = self.geo_agent.distance_meters(
                    lat, lon,
                    float(candidate_lat), float(candidate_lon),
                )
                # Full score if within 50m, decay to 0 at 500m
                if distance < 50:
                    score += 0.2
                elif distance < 500:
                    score += 0.2 * (1 - distance / 500)
        
        return min(score, 1.0)
    
    def _name_similarity(self, name1: str, name2: str) -> float:
        """Simple name similarity based on word overlap"""
        if not name1 or not name2:
            return 0.0
        
        words1 = set(name1.upper().split())
        words2 = set(name2.upper().split())
        
        # Remove common words
        stopwords = {"THE", "A", "AN", "OF", "AND", "&", "INC", "LLC", "CO", "CORP"}
        words1 = words1 - stopwords
        words2 = words2 - stopwords
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0
    
    def _build_resolved_entity(
        self,
        candidate: Dict[str, Any],
        score: float,
        normalized_address: NormalizedAddress = None,
        source_records: List[Dict[str, Any]] = None,
        data_gaps: List[str] = None,
    ) -> ResolvedEntity:
        """Build resolved entity from candidate"""
        # Get geo information
        geo = self.geo_agent.resolve_from_registry(candidate)
        
        # Determine join strategy based on what we have
        if score > 0.8 and normalized_address:
            join_strategy = "exact_address"
        elif geo.latitude and geo.longitude:
            join_strategy = "spatial_radius"
        else:
            join_strategy = "neighborhood_aggregate"
        
        # Generate entity ID
        entity_id = candidate.get("business_id") or candidate.get("entity_id")
        if not entity_id:
            entity_id = f"ent_{normalized_address.hash_key[:8]}" if normalized_address else "ent_unknown"
        
        return ResolvedEntity(
            entity_id=str(entity_id),
            business_name=candidate.get("business_name") or candidate.get("dba_name", "Unknown"),
            address=candidate.get("address", ""),
            normalized_address=normalized_address.normalized if normalized_address else "",
            latitude=geo.latitude,
            longitude=geo.longitude,
            geohash=geo.geohash,
            neighborhood=geo.neighborhood or candidate.get("neighborhood"),
            match_confidence=round(score, 3),
            join_strategy=join_strategy,
            source_records=source_records or [],
            data_gaps=data_gaps or [],
        )
    
    def _build_entity_from_input(
        self,
        business_name: str = None,
        address: str = None,
        normalized_address: NormalizedAddress = None,
        lat: float = None,
        lon: float = None,
        data_gaps: List[str] = None,
    ) -> ResolvedEntity:
        """Build entity from input when no registry match"""
        data_gaps = data_gaps or []
        data_gaps.append("No registry match found - using input data only")
        
        # Get geo info
        geo = self.geo_agent.resolve(lat=lat, lon=lon, address=address)
        
        # Determine join strategy
        if geo.latitude and geo.longitude:
            join_strategy = "spatial_radius"
        elif normalized_address:
            join_strategy = "neighborhood_aggregate"
        else:
            join_strategy = "neighborhood_aggregate"
        
        entity_id = f"ent_{normalized_address.hash_key[:8]}" if normalized_address else "ent_input"
        
        return ResolvedEntity(
            entity_id=entity_id,
            business_name=business_name or "Unknown Business",
            address=address or "",
            normalized_address=normalized_address.normalized if normalized_address else "",
            latitude=geo.latitude,
            longitude=geo.longitude,
            geohash=geo.geohash,
            neighborhood=geo.neighborhood,
            match_confidence=0.3,  # Low confidence for input-only resolution
            join_strategy=join_strategy,
            source_records=[],
            data_gaps=data_gaps,
        )
    
    def _empty_entity(self, data_gaps: List[str]) -> ResolvedEntity:
        """Return empty entity when resolution fails"""
        return ResolvedEntity(
            entity_id="ent_unresolved",
            business_name="Unresolved",
            address="",
            normalized_address="",
            latitude=None,
            longitude=None,
            geohash=None,
            neighborhood=None,
            match_confidence=0.0,
            join_strategy="neighborhood_aggregate",
            source_records=[],
            data_gaps=data_gaps,
        )
    
    def requires_confirmation(self, entity: ResolvedEntity) -> bool:
        """Check if entity resolution needs user confirmation"""
        return entity.match_confidence < self.CONFIDENCE_THRESHOLD
