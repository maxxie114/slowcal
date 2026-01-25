"""
Evidence Packager Agent

Creates a compact, model-friendly EvidencePack for LLM consumption.
Converts raw signals and risk drivers into a concise context package.

This is a deterministic agent (no LLM needed) that prepares data for
subsequent Nemotron agents.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class EvidenceItem:
    """Individual evidence snippet"""
    id: str
    content: str
    source: str
    date: Optional[str] = None


@dataclass
class TopDriver:
    """Risk driver with evidence"""
    driver: str
    direction: str  # "up", "down", "stable"
    contribution: float = 0.0
    evidence_refs: List[str] = field(default_factory=list)


@dataclass
class EvidencePack:
    """Compact evidence package for LLM context"""
    entity_summary: str
    risk_score: float
    risk_band: str
    top_drivers: List[TopDriver]
    as_of: str
    horizon_months: int
    signal_summaries: Dict[str, str] = field(default_factory=dict)
    evidence_items: List[EvidenceItem] = field(default_factory=list)
    data_gaps: List[str] = field(default_factory=list)
    confidence_notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result["top_drivers"] = [asdict(d) for d in self.top_drivers]
        result["evidence_items"] = [asdict(e) for e in self.evidence_items]
        return result


class EvidencePackagerAgent:
    """
    Agent that packages evidence for LLM consumption.
    
    Creates compact, model-friendly EvidencePack containing:
    - Top signals summarized by category
    - Top risk drivers with evidence IDs
    - Evidence snippets with unique IDs
    - Data gaps and uncertainty notes
    
    This is a deterministic agent (no LLM) that prepares structured
    data for narrative/strategy agents.
    
    Example:
        packager = EvidencePackagerAgent()
        evidence_pack = packager.package(
            entity=resolved_entity,
            signals=all_signals,
            risk_result=risk_model_output,
            as_of=analysis_timestamp,
            horizon_months=6
        )
    """
    
    VERSION = "1.0.0"
    MAX_EVIDENCE_ITEMS = 20
    MAX_SIGNAL_CHARS = 300
    
    def __init__(self, max_evidence_items: int = None):
        self.max_evidence_items = max_evidence_items or self.MAX_EVIDENCE_ITEMS
        self.evidence_counter = 0
    
    def package(
        self,
        entity: Dict[str, Any],
        signals: Dict[str, Any],
        risk_result: Dict[str, Any],
        as_of: datetime,
        horizon_months: int = 6,
    ) -> EvidencePack:
        """
        Package all evidence into a compact format for LLM.
        
        Args:
            entity: Resolved entity information
            signals: Raw signals from all data agents
            risk_result: Output from RiskModelAgent
            as_of: Analysis reference timestamp
            horizon_months: Forecast horizon
            
        Returns:
            EvidencePack ready for LLM consumption
        """
        self.evidence_counter = 0
        
        print(f"[PACKAGER] Starting package...")
        
        # Build entity summary
        print(f"[PACKAGER] Building entity summary...")
        entity_summary = self._build_entity_summary(entity)
        print(f"[PACKAGER] Entity summary: {entity_summary}")
        
        # Extract and format top drivers with evidence
        print(f"[PACKAGER] Extracting drivers...")
        raw_drivers = risk_result.get("top_drivers", [])
        print(f"[PACKAGER] Raw drivers type: {type(raw_drivers)}, count: {len(raw_drivers) if isinstance(raw_drivers, list) else 'N/A'}")
        top_drivers, driver_evidence = self._extract_drivers(raw_drivers, signals)
        print(f"[PACKAGER] Drivers extracted")
        
        # Summarize signals by category
        print(f"[PACKAGER] Summarizing signals...")
        signal_summaries = self._summarize_signals(signals)
        print(f"[PACKAGER] Signals summarized")
        
        # Collect key evidence items
        print(f"[PACKAGER] Collecting evidence...")
        evidence_items = self._collect_evidence(signals, driver_evidence)
        print(f"[PACKAGER] Evidence collected")
        
        # Identify data gaps
        print(f"[PACKAGER] Identifying data gaps...")
        data_gaps = self._identify_data_gaps(signals)
        print(f"[PACKAGER] Data gaps identified")
        
        # Add confidence notes
        confidence_notes = self._build_confidence_notes(entity, risk_result)
        
        return EvidencePack(
            entity_summary=entity_summary,
            risk_score=risk_result.get("risk_score", risk_result.get("score", 0.0)),
            risk_band=risk_result.get("risk_band", risk_result.get("band", "medium")),
            top_drivers=top_drivers,
            as_of=as_of.isoformat(),
            horizon_months=horizon_months,
            signal_summaries=signal_summaries,
            evidence_items=evidence_items,
            data_gaps=data_gaps,
            confidence_notes=confidence_notes,
        )
    
    def _build_entity_summary(self, entity: Dict[str, Any]) -> str:
        """Create a brief entity description"""
        parts = []
        
        if entity.get("business_name"):
            parts.append(entity["business_name"])
        
        if entity.get("business_type"):
            parts.append(f"({entity['business_type']})")
        
        if entity.get("address"):
            parts.append(f"at {entity['address']}")
        
        if entity.get("neighborhood"):
            parts.append(f"in {entity['neighborhood']}")
        
        return " ".join(parts) if parts else "Unknown business"
    
    def _extract_drivers(
        self,
        raw_drivers: List[Dict[str, Any]],
        signals: Dict[str, Any]
    ) -> tuple:
        """Extract top drivers and link to evidence"""
        top_drivers = []
        evidence_mapping = {}
        
        for driver_data in raw_drivers[:5]:  # Top 5 drivers
            driver_name = driver_data.get("driver", driver_data.get("feature", "unknown"))
            direction = driver_data.get("direction", "stable")
            contribution = driver_data.get("contribution", driver_data.get("importance", 0.0))
            
            # Find evidence for this driver
            evidence_refs = self._find_evidence_for_driver(driver_name, signals)
            evidence_mapping[driver_name] = evidence_refs
            
            top_drivers.append(TopDriver(
                driver=driver_name,
                direction=direction,
                contribution=contribution,
                evidence_refs=evidence_refs,
            ))
        
        return top_drivers, evidence_mapping
    
    def _find_evidence_for_driver(
        self,
        driver_name: str,
        signals: Dict[str, Any]
    ) -> List[str]:
        """Find evidence references for a given driver"""
        evidence_refs = []
        driver_lower = driver_name.lower()
        
        # Map driver names to signal categories
        category_mapping = {
            "311": "complaints_311",
            "complaint": "complaints_311",
            "permit": "permits",
            "dbi": "dbi_complaints",
            "sfpd": "sfpd_incidents",
            "incident": "sfpd_incidents",
            "crime": "sfpd_incidents",
            "eviction": "evictions",
            "vacancy": "vacancy",
        }
        
        for keyword, category in category_mapping.items():
            if keyword in driver_lower:
                if category in signals:
                    # Generate evidence ID for this category
                    eid = self._generate_evidence_id(category)
                    evidence_refs.append(eid)
                break
        
        return evidence_refs
    
    def _generate_evidence_id(self, source: str) -> str:
        """Generate unique evidence ID"""
        self.evidence_counter += 1
        return f"e:{source}-{self.evidence_counter:03d}"
    
    def _summarize_signals(self, signals: Dict[str, Any]) -> Dict[str, str]:
        """Create brief summaries for each signal category"""
        summaries = {}
        
        # Permits
        if "permits" in signals:
            p = signals["permits"]
            count_12m = p.get("permit_count_12m", 0)
            trend = p.get("permit_trend", "stable")
            summaries["permits"] = f"{count_12m} permits in last 12mo, trend: {trend}"
        
        # 311 Complaints
        if "complaints_311" in signals:
            c = signals["complaints_311"]
            count_6m = c.get("count_6m", 0)
            top_cats = c.get("top_categories", [])[:3]
            cats_str = ", ".join(top_cats) if top_cats else "various"
            summaries["complaints_311"] = f"{count_6m} complaints in 6mo; top: {cats_str}"
        
        # DBI Complaints
        if "dbi_complaints" in signals:
            d = signals["dbi_complaints"]
            count = d.get("complaint_count_12m", 0)
            open_ratio = d.get("open_closed_ratio", 0)
            summaries["dbi_complaints"] = f"{count} DBI complaints in 12mo, open ratio: {open_ratio:.2f}"
        
        # SFPD Incidents
        if "sfpd_incidents" in signals:
            s = signals["sfpd_incidents"]
            count = s.get("incident_count_6m", 0)
            top_cats = s.get("top_categories", [])[:2]
            cats_str = ", ".join(top_cats) if top_cats else "various"
            summaries["sfpd_incidents"] = f"{count} incidents nearby in 6mo; top: {cats_str}"
        
        # Evictions
        if "evictions" in signals:
            e = signals["evictions"]
            rate = e.get("eviction_rate_12m", 0)
            trend = e.get("trend", "stable")
            summaries["evictions"] = f"Neighborhood eviction rate: {rate:.1%}, trend: {trend}"
        
        # Vacancy
        if "vacancy" in signals:
            v = signals["vacancy"]
            rate = v.get("vacancy_rate", 0)
            trend = v.get("trend", "stable")
            summaries["vacancy"] = f"Corridor vacancy rate: {rate:.1%}, trend: {trend}"
        
        return summaries
    
    def _collect_evidence(
        self,
        signals: Dict[str, Any],
        driver_evidence: Dict[str, List[str]]
    ) -> List[EvidenceItem]:
        """Collect evidence items from signals"""
        items = []
        
        # Get all evidence refs from drivers
        all_refs = set()
        for refs in driver_evidence.values():
            all_refs.update(refs)
        
        # Create evidence items for each category
        evidence_sources = [
            ("permits", "permits"),
            ("complaints_311", "311 Cases"),
            ("dbi_complaints", "DBI Complaints"),
            ("sfpd_incidents", "SFPD Incidents"),
            ("evictions", "Eviction Notices"),
            ("vacancy", "Commercial Vacancy"),
        ]
        
        for source_key, source_name in evidence_sources:
            if source_key in signals:
                signal_data = signals[source_key]
                
                # Create evidence summary for this source
                evidence_refs = signal_data.get("evidence_refs", [])
                
                # Add top items as evidence
                if source_key == "complaints_311":
                    for i, cat in enumerate(signal_data.get("top_categories", [])[:3]):
                        count = signal_data.get("category_counts", {}).get(cat, 0)
                        items.append(EvidenceItem(
                            id=f"e:{source_key}-{i+1:03d}",
                            content=f"{cat}: {count} complaints",
                            source=source_name,
                        ))
                
                elif source_key == "sfpd_incidents":
                    for i, cat in enumerate(signal_data.get("top_categories", [])[:3]):
                        items.append(EvidenceItem(
                            id=f"e:{source_key}-{i+1:03d}",
                            content=f"Incident category: {cat}",
                            source=source_name,
                        ))
                
                else:
                    # Generic evidence item
                    freshness = signal_data.get("freshness", {})
                    # Handle case where freshness is a string (timestamp) not a dict
                    as_of_date = None
                    if isinstance(freshness, dict):
                        as_of_date = freshness.get("as_of")
                    elif isinstance(freshness, str):
                        as_of_date = freshness
                    items.append(EvidenceItem(
                        id=f"e:{source_key}-001",
                        content=f"Data from {source_name}: {self._summarize_signals({source_key: signal_data}).get(source_key, 'available')}",
                        source=source_name,
                        date=as_of_date,
                    ))
        
        return items[:self.max_evidence_items]
    
    def _identify_data_gaps(self, signals: Dict[str, Any]) -> List[str]:
        """Identify missing or stale data"""
        gaps = []
        
        expected_sources = [
            "permits",
            "complaints_311",
            "dbi_complaints",
            "sfpd_incidents",
            "evictions",
            "vacancy",
        ]
        
        for source in expected_sources:
            if source not in signals:
                gaps.append(f"Missing data: {source}")
            else:
                signal_data = signals[source]
                
                # Check for explicit data gaps
                if "data_gaps" in signal_data:
                    gaps.extend(signal_data["data_gaps"])
                
                # Check freshness
                freshness = signal_data.get("freshness", {})
                # Handle case where freshness is a string (timestamp) not a dict
                if isinstance(freshness, dict) and freshness.get("is_stale"):
                    gaps.append(f"Stale data: {source} (last updated: {freshness.get('last_updated', 'unknown')})")
        
        return gaps
    
    def _build_confidence_notes(
        self,
        entity: Dict[str, Any],
        risk_result: Dict[str, Any]
    ) -> List[str]:
        """Build confidence and uncertainty notes"""
        notes = []
        
        # Entity match confidence
        match_confidence = entity.get("match_confidence", 1.0)
        if match_confidence < 0.8:
            notes.append(f"Entity match confidence: {match_confidence:.0%} - some uncertainty in business identification")
        elif match_confidence < 0.95:
            notes.append(f"Entity match confidence: {match_confidence:.0%}")
        
        # Model confidence
        model_confidence = risk_result.get("confidence", 1.0)
        if model_confidence < 0.7:
            notes.append(f"Model prediction confidence is lower than usual ({model_confidence:.0%})")
        
        # Join strategy note
        join_strategy = entity.get("join_strategy")
        if join_strategy == "spatial radius":
            notes.append("Analysis based on spatial proximity (exact address match not available)")
        elif join_strategy == "neighborhood aggregate":
            notes.append("Using neighborhood-level aggregates (no direct address match)")
        
        return notes
    
    def get_version(self) -> str:
        """Return agent version"""
        return self.VERSION
