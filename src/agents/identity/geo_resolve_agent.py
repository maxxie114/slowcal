"""
Geo Resolve Agent

Handles geocoding and spatial join key generation.
Provides lat/lon resolution and geohash keys for spatial queries.
"""

import logging
import math
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GeoLocation:
    """Resolved geographic location"""
    latitude: Optional[float]
    longitude: Optional[float]
    geohash: Optional[str]
    neighborhood: Optional[str]
    supervisor_district: Optional[str]
    resolution_method: str  # "registry", "geocoded", "approximate"
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "geohash": self.geohash,
            "neighborhood": self.neighborhood,
            "supervisor_district": self.supervisor_district,
            "resolution_method": self.resolution_method,
            "confidence": self.confidence,
        }


class GeoResolveAgent:
    """
    Agent for geographic resolution and spatial key generation.
    
    Provides:
    - Geocoding (address to lat/lon)
    - Geohash generation for spatial joins
    - Neighborhood resolution
    
    Example usage:
        agent = GeoResolveAgent()
        location = agent.resolve_from_registry(registry_record)
        print(location.geohash)  # "9q8yyk3"
    """
    
    VERSION = "0.1"
    
    # San Francisco bounding box (approximate)
    SF_BOUNDS = {
        "min_lat": 37.6,
        "max_lat": 37.85,
        "min_lon": -122.55,
        "max_lon": -122.35,
    }
    
    # Geohash base32 alphabet
    GEOHASH_ALPHABET = "0123456789bcdefghjkmnpqrstuvwxyz"
    
    @property
    def name(self) -> str:
        return "GeoResolveAgent"
    
    def resolve_from_registry(
        self,
        registry_record: Dict[str, Any],
    ) -> GeoLocation:
        """
        Extract geo information from a business registry record.
        
        Args:
            registry_record: Record from BusinessRegistryAgent
        
        Returns:
            GeoLocation with resolved coordinates
        """
        lat = None
        lon = None
        neighborhood = None
        district = None
        
        # Extract from record
        if registry_record:
            lat = registry_record.get("latitude")
            lon = registry_record.get("longitude")
            neighborhood = registry_record.get("neighborhood")
            district = registry_record.get("supervisor_district")
            
            # Try to get from nested location field
            if not lat or not lon:
                location = registry_record.get("business_location", {})
                if isinstance(location, dict):
                    lat = location.get("latitude")
                    lon = location.get("longitude")
        
        # Validate coordinates are in SF
        if lat and lon:
            lat = float(lat)
            lon = float(lon)
            if not self._is_in_sf(lat, lon):
                logger.warning(f"Coordinates ({lat}, {lon}) outside SF bounds")
                lat, lon = None, None
        
        # Generate geohash if we have coordinates
        geohash = None
        if lat and lon:
            geohash = self.encode_geohash(lat, lon)
        
        return GeoLocation(
            latitude=lat,
            longitude=lon,
            geohash=geohash,
            neighborhood=neighborhood,
            supervisor_district=district,
            resolution_method="registry" if lat and lon else "unknown",
            confidence=0.95 if lat and lon else 0.0,
        )
    
    def geocode_address(
        self,
        address: str,
        city: str = "San Francisco",
        state: str = "CA",
    ) -> GeoLocation:
        """
        Geocode an address to lat/lon.
        
        Note: This is a placeholder. In production, use a geocoding service.
        
        Args:
            address: Street address
            city: City
            state: State
        
        Returns:
            GeoLocation with geocoded coordinates
        """
        # TODO: Integrate with geocoding service (Census, Google, etc.)
        # For now, return unknown location
        logger.warning("Geocoding not implemented - returning unknown location")
        
        return GeoLocation(
            latitude=None,
            longitude=None,
            geohash=None,
            neighborhood=None,
            supervisor_district=None,
            resolution_method="geocoding_unavailable",
            confidence=0.0,
        )
    
    def resolve(
        self,
        lat: float = None,
        lon: float = None,
        address: str = None,
        registry_record: Dict[str, Any] = None,
    ) -> GeoLocation:
        """
        Resolve geographic location from any available source.
        
        Priority:
        1. Explicit lat/lon
        2. Registry record
        3. Geocoding (if implemented)
        """
        # Try explicit coordinates first
        if lat and lon:
            if self._is_in_sf(lat, lon):
                return GeoLocation(
                    latitude=lat,
                    longitude=lon,
                    geohash=self.encode_geohash(lat, lon),
                    neighborhood=None,
                    supervisor_district=None,
                    resolution_method="explicit",
                    confidence=1.0,
                )
        
        # Try registry record
        if registry_record:
            result = self.resolve_from_registry(registry_record)
            if result.latitude and result.longitude:
                return result
        
        # Try geocoding
        if address:
            return self.geocode_address(address)
        
        # No resolution possible
        return GeoLocation(
            latitude=None,
            longitude=None,
            geohash=None,
            neighborhood=None,
            supervisor_district=None,
            resolution_method="unresolved",
            confidence=0.0,
        )
    
    def encode_geohash(
        self,
        lat: float,
        lon: float,
        precision: int = 7,
    ) -> str:
        """
        Encode lat/lon to geohash string.
        
        Precision 7 gives ~150m x 150m grid cells.
        
        Args:
            lat: Latitude
            lon: Longitude
            precision: Geohash length (default 7)
        
        Returns:
            Geohash string
        """
        lat_range = (-90.0, 90.0)
        lon_range = (-180.0, 180.0)
        
        geohash = []
        bits = [16, 8, 4, 2, 1]
        bit = 0
        ch = 0
        even = True
        
        while len(geohash) < precision:
            if even:
                mid = (lon_range[0] + lon_range[1]) / 2
                if lon >= mid:
                    ch |= bits[bit]
                    lon_range = (mid, lon_range[1])
                else:
                    lon_range = (lon_range[0], mid)
            else:
                mid = (lat_range[0] + lat_range[1]) / 2
                if lat >= mid:
                    ch |= bits[bit]
                    lat_range = (mid, lat_range[1])
                else:
                    lat_range = (lat_range[0], mid)
            
            even = not even
            
            if bit < 4:
                bit += 1
            else:
                geohash.append(self.GEOHASH_ALPHABET[ch])
                bit = 0
                ch = 0
        
        return "".join(geohash)
    
    def decode_geohash(self, geohash: str) -> Tuple[float, float]:
        """
        Decode geohash to lat/lon (center point).
        
        Returns:
            Tuple of (latitude, longitude)
        """
        lat_range = (-90.0, 90.0)
        lon_range = (-180.0, 180.0)
        
        bits = [16, 8, 4, 2, 1]
        even = True
        
        for char in geohash:
            idx = self.GEOHASH_ALPHABET.index(char.lower())
            for bit in bits:
                if even:
                    mid = (lon_range[0] + lon_range[1]) / 2
                    if idx & bit:
                        lon_range = (mid, lon_range[1])
                    else:
                        lon_range = (lon_range[0], mid)
                else:
                    mid = (lat_range[0] + lat_range[1]) / 2
                    if idx & bit:
                        lat_range = (mid, lat_range[1])
                    else:
                        lat_range = (lat_range[0], mid)
                even = not even
        
        lat = (lat_range[0] + lat_range[1]) / 2
        lon = (lon_range[0] + lon_range[1]) / 2
        
        return lat, lon
    
    def geohash_neighbors(self, geohash: str) -> Dict[str, str]:
        """
        Get neighboring geohashes (8 surrounding cells).
        
        Returns:
            Dict with keys: n, ne, e, se, s, sw, w, nw
        """
        lat, lon = self.decode_geohash(geohash)
        precision = len(geohash)
        
        # Approximate cell size at this precision
        lat_delta = 180.0 / (32 ** (precision // 2))
        lon_delta = 360.0 / (32 ** ((precision + 1) // 2))
        
        neighbors = {
            "n": self.encode_geohash(lat + lat_delta, lon, precision),
            "ne": self.encode_geohash(lat + lat_delta, lon + lon_delta, precision),
            "e": self.encode_geohash(lat, lon + lon_delta, precision),
            "se": self.encode_geohash(lat - lat_delta, lon + lon_delta, precision),
            "s": self.encode_geohash(lat - lat_delta, lon, precision),
            "sw": self.encode_geohash(lat - lat_delta, lon - lon_delta, precision),
            "w": self.encode_geohash(lat, lon - lon_delta, precision),
            "nw": self.encode_geohash(lat + lat_delta, lon - lon_delta, precision),
        }
        
        return neighbors
    
    def distance_meters(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """
        Calculate distance between two points in meters (Haversine formula).
        """
        R = 6371000  # Earth radius in meters
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def _is_in_sf(self, lat: float, lon: float) -> bool:
        """Check if coordinates are within SF bounds"""
        return (
            self.SF_BOUNDS["min_lat"] <= lat <= self.SF_BOUNDS["max_lat"] and
            self.SF_BOUNDS["min_lon"] <= lon <= self.SF_BOUNDS["max_lon"]
        )
