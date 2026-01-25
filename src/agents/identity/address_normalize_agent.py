"""
Address Normalize Agent

Normalizes address strings to standard format for consistent matching.
Handles:
- Suite/unit variations
- Street suffix standardization
- Punctuation normalization
- Case normalization
"""

import logging
import re
import hashlib
from typing import Any, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class NormalizedAddress:
    """Normalized address with components"""
    original: str
    normalized: str
    street_number: Optional[str]
    street_name: Optional[str]
    street_suffix: Optional[str]
    unit: Optional[str]
    city: str
    state: str
    zip_code: Optional[str]
    hash_key: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "original": self.original,
            "normalized": self.normalized,
            "street_number": self.street_number,
            "street_name": self.street_name,
            "street_suffix": self.street_suffix,
            "unit": self.unit,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "hash_key": self.hash_key,
        }


class AddressNormalizeAgent:
    """
    Agent for normalizing street addresses.
    
    Produces standardized address strings and hash keys for matching.
    
    Example usage:
        agent = AddressNormalizeAgent()
        result = agent.normalize("123 Main St., Suite 100, San Francisco, CA 94102")
        print(result.normalized)  # "123 MAIN STREET #100 SAN FRANCISCO CA 94102"
    """
    
    VERSION = "0.1"
    
    # Street suffix standardization
    SUFFIX_MAP = {
        "st": "STREET", "st.": "STREET", "street": "STREET",
        "ave": "AVENUE", "ave.": "AVENUE", "avenue": "AVENUE",
        "blvd": "BOULEVARD", "blvd.": "BOULEVARD", "boulevard": "BOULEVARD",
        "dr": "DRIVE", "dr.": "DRIVE", "drive": "DRIVE",
        "ln": "LANE", "ln.": "LANE", "lane": "LANE",
        "rd": "ROAD", "rd.": "ROAD", "road": "ROAD",
        "ct": "COURT", "ct.": "COURT", "court": "COURT",
        "pl": "PLACE", "pl.": "PLACE", "place": "PLACE",
        "cir": "CIRCLE", "cir.": "CIRCLE", "circle": "CIRCLE",
        "way": "WAY",
        "ter": "TERRACE", "ter.": "TERRACE", "terrace": "TERRACE",
        "pkwy": "PARKWAY", "parkway": "PARKWAY",
        "hwy": "HIGHWAY", "highway": "HIGHWAY",
        "aly": "ALLEY", "alley": "ALLEY",
    }
    
    # Unit designator standardization
    UNIT_MAP = {
        "suite": "#", "ste": "#", "ste.": "#",
        "unit": "#", "apt": "#", "apt.": "#",
        "apartment": "#", "room": "#", "rm": "#",
        "floor": "FL", "fl": "FL", "fl.": "FL",
        "#": "#",
    }
    
    # Direction standardization
    DIRECTION_MAP = {
        "n": "N", "n.": "N", "north": "N",
        "s": "S", "s.": "S", "south": "S",
        "e": "E", "e.": "E", "east": "E",
        "w": "W", "w.": "W", "west": "W",
        "ne": "NE", "n.e.": "NE", "northeast": "NE",
        "nw": "NW", "n.w.": "NW", "northwest": "NW",
        "se": "SE", "s.e.": "SE", "southeast": "SE",
        "sw": "SW", "s.w.": "SW", "southwest": "SW",
    }
    
    @property
    def name(self) -> str:
        return "AddressNormalizeAgent"
    
    def normalize(
        self,
        address: str,
        city: str = "San Francisco",
        state: str = "CA",
    ) -> NormalizedAddress:
        """
        Normalize an address string.
        
        Args:
            address: Raw address string
            city: City (defaults to San Francisco)
            state: State (defaults to CA)
        
        Returns:
            NormalizedAddress with standardized components
        """
        if not address:
            return self._empty_result()
        
        original = address
        
        # Step 1: Basic cleanup
        normalized = address.strip()
        normalized = re.sub(r'\s+', ' ', normalized)  # Collapse whitespace
        
        # Step 2: Extract and remove city, state, zip if present
        zip_code = self._extract_zip(normalized)
        normalized = self._remove_city_state_zip(normalized, city, state)
        
        # Step 3: Parse components
        street_number, street_name, street_suffix, unit = self._parse_street(normalized)
        
        # Step 4: Standardize components
        if street_suffix:
            street_suffix = self.SUFFIX_MAP.get(street_suffix.lower(), street_suffix.upper())
        
        if street_name:
            street_name = self._standardize_directions(street_name)
            street_name = street_name.upper()
        
        # Step 5: Rebuild normalized address
        parts = []
        if street_number:
            parts.append(street_number)
        if street_name:
            parts.append(street_name)
        if street_suffix:
            parts.append(street_suffix)
        if unit:
            parts.append(f"#{unit}")
        
        parts.append(city.upper())
        parts.append(state.upper())
        
        if zip_code:
            parts.append(zip_code)
        
        normalized_str = " ".join(parts)
        
        # Generate hash key for matching
        hash_key = self._generate_hash(normalized_str)
        
        return NormalizedAddress(
            original=original,
            normalized=normalized_str,
            street_number=street_number,
            street_name=street_name,
            street_suffix=street_suffix,
            unit=unit,
            city=city.upper(),
            state=state.upper(),
            zip_code=zip_code,
            hash_key=hash_key,
        )
    
    def _empty_result(self) -> NormalizedAddress:
        return NormalizedAddress(
            original="",
            normalized="",
            street_number=None,
            street_name=None,
            street_suffix=None,
            unit=None,
            city="SAN FRANCISCO",
            state="CA",
            zip_code=None,
            hash_key="",
        )
    
    def _extract_zip(self, address: str) -> Optional[str]:
        """Extract ZIP code from address"""
        # Match 5-digit or 9-digit ZIP
        match = re.search(r'\b(\d{5}(?:-\d{4})?)\b', address)
        return match.group(1) if match else None
    
    def _remove_city_state_zip(self, address: str, city: str, state: str) -> str:
        """Remove city, state, and ZIP from address"""
        # Remove ZIP codes
        address = re.sub(r'\b\d{5}(?:-\d{4})?\b', '', address)
        
        # Remove state
        address = re.sub(rf'\b{state}\b', '', address, flags=re.IGNORECASE)
        address = re.sub(r'\b(california|calif\.?)\b', '', address, flags=re.IGNORECASE)
        
        # Remove city
        address = re.sub(rf'\b{city}\b', '', address, flags=re.IGNORECASE)
        address = re.sub(r'\bsf\b', '', address, flags=re.IGNORECASE)
        
        # Clean up remaining punctuation and whitespace
        address = re.sub(r'[,]+', ' ', address)
        address = re.sub(r'\s+', ' ', address)
        
        return address.strip()
    
    def _parse_street(self, address: str) -> tuple:
        """Parse street address into components"""
        address = address.strip()
        
        # Extract unit first
        unit = None
        for unit_type in ["suite", "ste", "ste.", "unit", "apt", "apt.", "apartment", "room", "rm", "#"]:
            pattern = rf'{unit_type}\s*[#]?\s*(\w+)'
            match = re.search(pattern, address, re.IGNORECASE)
            if match:
                unit = match.group(1)
                address = re.sub(pattern, '', address, flags=re.IGNORECASE)
                break
        
        # Clean up
        address = re.sub(r'[,]+', ' ', address)
        address = re.sub(r'\s+', ' ', address).strip()
        
        parts = address.split()
        if not parts:
            return None, None, None, unit
        
        # First part is usually street number
        street_number = None
        if parts and re.match(r'^\d+[a-zA-Z]?$', parts[0]):
            street_number = parts[0]
            parts = parts[1:]
        
        # Last part might be suffix
        street_suffix = None
        if parts and parts[-1].lower().rstrip('.') in self.SUFFIX_MAP:
            street_suffix = parts[-1]
            parts = parts[:-1]
        
        # Remaining parts are street name
        street_name = " ".join(parts) if parts else None
        
        return street_number, street_name, street_suffix, unit
    
    def _standardize_directions(self, text: str) -> str:
        """Standardize directional prefixes/suffixes"""
        words = text.split()
        result = []
        for word in words:
            lower = word.lower().rstrip('.')
            if lower in self.DIRECTION_MAP:
                result.append(self.DIRECTION_MAP[lower])
            else:
                result.append(word)
        return " ".join(result)
    
    def _generate_hash(self, normalized: str) -> str:
        """Generate stable hash key for address matching"""
        # Remove all non-alphanumeric for hash
        clean = re.sub(r'[^a-zA-Z0-9]', '', normalized.lower())
        return hashlib.md5(clean.encode()).hexdigest()[:12]
    
    def match_score(self, addr1: str, addr2: str) -> float:
        """
        Calculate similarity score between two addresses.
        
        Returns:
            Float 0-1 indicating match confidence
        """
        n1 = self.normalize(addr1)
        n2 = self.normalize(addr2)
        
        # Exact hash match
        if n1.hash_key == n2.hash_key:
            return 1.0
        
        # Component matching
        score = 0.0
        
        if n1.street_number == n2.street_number and n1.street_number:
            score += 0.3
        
        if n1.street_name and n2.street_name:
            # Simple string similarity
            if n1.street_name == n2.street_name:
                score += 0.4
            elif n1.street_name in n2.street_name or n2.street_name in n1.street_name:
                score += 0.2
        
        if n1.street_suffix == n2.street_suffix and n1.street_suffix:
            score += 0.1
        
        if n1.zip_code == n2.zip_code and n1.zip_code:
            score += 0.2
        
        return min(score, 1.0)
