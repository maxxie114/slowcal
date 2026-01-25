"""
Case Manager Agent - Main Orchestrator

Runs the complete risk analysis pipeline by coordinating all specialist agents.

Responsibilities:
- Run the pipeline deterministically (parallelize data agents where possible)
- Maintain CaseContext state: time horizon, as_of timestamp, entity keys
- Enforce schema validation at each hop
- Decide which optional agents to invoke based on business type and missing data

This is the main entry point for risk analysis.
"""

import logging
import uuid
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
import math

logger = logging.getLogger(__name__)

# Debug mode - set via environment variable or default True for development
DEBUG_AGENTS = os.getenv("DEBUG_AGENTS", "true").lower() in ("true", "1", "yes")

def debug_print(message: str, agent_name: str = None, direction: str = None):
    """Print debug messages for agent communication"""
    if not DEBUG_AGENTS:
        return
    
    # Color codes for terminal output
    COLORS = {
        "send": "\033[94m",      # Blue - sending to agent
        "receive": "\033[92m",   # Green - receiving from agent
        "error": "\033[91m",     # Red - error
        "info": "\033[93m",      # Yellow - info
        "reset": "\033[0m",      # Reset
    }
    
    color = COLORS.get(direction, COLORS["info"])
    reset = COLORS["reset"]
    
    if direction == "send":
        arrow = "→"
        prefix = f"📤 {agent_name}"
    elif direction == "receive":
        arrow = "←"
        prefix = f"📥 {agent_name}"
    else:
        arrow = "•"
        prefix = f"🔧 {agent_name}" if agent_name else "🔧"
    
    print(f"{color}[AGENT] {prefix} {arrow} {message}{reset}")


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance between two lat/lon points in kilometers."""
    # Convert degrees to radians
    rlat1, rlon1, rlat2, rlon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(min(1, math.sqrt(a)))
    return 6371.0 * c

# Import path handling
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import tools
from tools.schema_validation import SchemaValidator
from tools.nim_client import NIMClient

# Import data agents
from agents.data import (
    BusinessRegistryAgent,
    PermitsAgent,
    Complaints311Agent,
    DBIComplaintsAgent,
    SFPDIncidentsAgent,
    EvictionsAgent,
    VacancyCorridorAgent,
)

# Import identity agents
from agents.identity import (
    AddressNormalizeAgent,
    GeoResolveAgent,
    EntityResolverAgent,
)

# Import ML agents
from agents.ml import (
    FeatureBuilderAgent,
    RiskModelAgent,
    DataFreshnessAgent,
)

# Import LLM agents
from agents.llm import (
    EvidencePackagerAgent,
    ExplanationAgent,
    StrategyPlannerAgent,
    CriticQAAgent,
    PolicyGuardAgent,
)


@dataclass
class CaseContext:
    """State maintained throughout the analysis pipeline"""
    def __init__(
        self,
        case_id: str,
        business_query: str,
        as_of: datetime,
        horizon_months: int = 6,
        business_name: Optional[str] = None,
        business_address: Optional[str] = None,
        entity_keys: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None,
        stages_completed: Optional[List[str]] = None,
        errors: Optional[List[Dict[str, Any]]] = None,
        warnings: Optional[List[str]] = None,
    ):
        self.case_id = case_id
        self.business_query = business_query
        self.as_of = as_of
        self.horizon_months = horizon_months
        self.business_name = business_name
        self.business_address = business_address
        self.entity_keys = entity_keys or {}
        self.options = options or {}
        self.stages_completed = stages_completed or []
        self.errors = errors or []
        self.warnings = warnings or []


@dataclass
class PipelineResult:
    """Result of the complete pipeline"""
    success: bool
    response: Dict[str, Any]
    context: CaseContext
    duration_ms: float


class CaseManagerAgent:
    """
    Main orchestrator that coordinates all specialist agents.
    
    Runs the complete risk analysis pipeline:
    1. Data acquisition (parallel)
    2. Entity resolution
    3. Feature building
    4. Risk scoring
    5. Evidence packaging
    6. Strategy generation
    7. Quality assurance
    
    Example:
        manager = CaseManagerAgent()
        result = manager.analyze(
            business_query="Blue Bottle Coffee, 300 Webster St",
            horizon_months=6
        )
    """
    
    VERSION = "1.0.0"
    
    def __init__(
        self,
        nim_client: NIMClient = None,
        max_workers: int = 5,
        enable_llm_agents: bool = True,
    ):
        """
        Initialize CaseManagerAgent.
        
        Args:
            nim_client: NIM client for LLM agents
            max_workers: Max parallel workers for data agents
            enable_llm_agents: Whether to run LLM-based agents
        """
        self.nim_client = nim_client or NIMClient(timeout=300.0)  # 5 min timeout for DGX
        self.max_workers = max_workers
        self.enable_llm_agents = enable_llm_agents
        self.use_synthetic = False
        self.use_supabase = False  # New flag
        self.validator = SchemaValidator()
        
        # Initialize agents
        self._init_agents()
    
    def _init_agents(self, use_synthetic: bool = False, use_supabase: bool = False):
        """Initialize all specialist agents"""
        self.use_synthetic = use_synthetic
        self.use_supabase = use_supabase
        
        # Data agents
        self.business_registry_agent = BusinessRegistryAgent(use_synthetic=use_synthetic, use_supabase=use_supabase)
        self.permits_agent = PermitsAgent(use_synthetic=use_synthetic, use_supabase=use_supabase)
        self.complaints_311_agent = Complaints311Agent(use_synthetic=use_synthetic, use_supabase=use_supabase)
        self.dbi_complaints_agent = DBIComplaintsAgent(use_synthetic=use_synthetic, use_supabase=use_supabase)
        self.sfpd_incidents_agent = SFPDIncidentsAgent(use_synthetic=use_synthetic, use_supabase=use_supabase)
        self.evictions_agent = EvictionsAgent(use_synthetic=use_synthetic, use_supabase=use_supabase)
        self.vacancy_agent = VacancyCorridorAgent(use_synthetic=use_synthetic, use_supabase=use_supabase)
        
        # Identity agents
        self.address_normalize_agent = AddressNormalizeAgent()
        self.geo_resolve_agent = GeoResolveAgent()
        self.entity_resolver_agent = EntityResolverAgent()
        
        # ML agents
        self.feature_builder_agent = FeatureBuilderAgent()
        self.risk_model_agent = RiskModelAgent()
        self.data_freshness_agent = DataFreshnessAgent()
        
        # LLM agents
        self.evidence_packager_agent = EvidencePackagerAgent()
        self.explanation_agent = ExplanationAgent(nim_client=self.nim_client)
        self.strategy_planner_agent = StrategyPlannerAgent(nim_client=self.nim_client)
        self.critic_qa_agent = CriticQAAgent(nim_client=self.nim_client)
        self.policy_guard_agent = PolicyGuardAgent()
    
    def analyze(
        self,
        business_query: str,
        as_of: datetime = None,
        horizon_months: int = 6,
        options: Dict[str, Any] = None,
    ) -> PipelineResult:
        """
        Run complete risk analysis for a business.
        
        Args:
            business_query: Business name and/or address
            as_of: Reference timestamp (default: now)
            horizon_months: Forecast horizon
            options: Additional options (skip_llm, focus_areas, etc.)
            
        Returns:
            PipelineResult with complete analysis
        """
        start_time = datetime.now()
        
        # Create case context
        context = CaseContext(
            case_id=str(uuid.uuid4()),
            business_query=business_query,
            as_of=as_of or datetime.now(),
            horizon_months=horizon_months,
            options=options or {},
        )
        
        # Re-initialize agents if mode changed
        use_synthetic = context.options.get("use_synthetic", False)
        use_supabase = context.options.get("use_supabase", False)
        
        if use_synthetic != self.use_synthetic or use_supabase != self.use_supabase:
            self._init_agents(use_synthetic=use_synthetic, use_supabase=use_supabase)
        
        # Parse business query to separate name and address
        parsed = self._parse_business_query(business_query)
        context.business_name = parsed.get("business_name")
        context.business_address = parsed.get("address")
        
        debug_print(f"Starting analysis pipeline for: {business_query}", "CaseManager", "info")
        debug_print(f"Case ID: {context.case_id}, Horizon: {horizon_months} months", "CaseManager", "info")
        
        try:
            # Stage 1: Data Acquisition (parallel)
            logger.info(f"[{context.case_id}] Stage 1: Data Acquisition")
            debug_print("Dispatching parallel data agents...", "CaseManager", "send")
            signals, registry_data = self._stage_data_acquisition(context)
            debug_print(f"Data acquired from {len(signals)} sources", "CaseManager", "receive")
            context.stages_completed.append("data_acquisition")
            
            # Stage 2: Entity Resolution
            logger.info(f"[{context.case_id}] Stage 2: Entity Resolution")
            debug_print(f"Resolving entity: {business_query}", "EntityResolver", "send")
            entity = self._stage_entity_resolution(context, registry_data)
            debug_print(f"Entity resolved: {entity.get('entity_id', 'unknown')} (confidence: {entity.get('match_confidence', 0):.0%})", "EntityResolver", "receive")
            context.stages_completed.append("entity_resolution")
            
            # Update context with entity keys
            context.entity_keys = {
                "entity_id": entity.get("entity_id"),
                "address": entity.get("address"),
                "lat": entity.get("lat"),
                "lon": entity.get("lon"),
                "neighborhood": entity.get("neighborhood"),
            }
            
            # Stage 3: Feature Building
            logger.info(f"[{context.case_id}] Stage 3: Feature Building")
            debug_print("Building ML features from signals...", "FeatureBuilder", "send")
            features = self._stage_feature_building(context, signals, entity)
            feature_count = len(features.features) if hasattr(features, 'features') else 0
            debug_print(f"Built {feature_count} features", "FeatureBuilder", "receive")
            context.stages_completed.append("feature_building")
            
            # Stage 4: Risk Scoring
            logger.info(f"[{context.case_id}] Stage 4: Risk Scoring")
            debug_print("Running risk model prediction...", "RiskModel", "send")
            risk_result = self._stage_risk_scoring(context, features)
            debug_print(f"Risk score: {risk_result.get('score', 0):.2f} ({risk_result.get('band', 'unknown')})", "RiskModel", "receive")
            context.stages_completed.append("risk_scoring")
            
            # Stage 5: Data Freshness Check
            logger.info(f"[{context.case_id}] Stage 5: Data Freshness Check")
            debug_print("Checking data freshness...", "DataFreshness", "send")
            freshness = self._stage_freshness_check(context, signals)
            all_fresh = freshness.get('all_fresh', True) if isinstance(freshness, dict) else True
            debug_print(f"Freshness check: {'✓ All fresh' if all_fresh else '⚠ Some stale'}", "DataFreshness", "receive")
            context.stages_completed.append("freshness_check")
            
            # Stage 6: Strategy Generation (LLM)
            strategy = {}
            explanation = {}
            if self.enable_llm_agents and not context.options.get("skip_llm"):
                logger.info(f"[{context.case_id}] Stage 6: Strategy Generation")
                debug_print("Calling Nemotron LLM for strategy generation...", "StrategyPlanner", "send")
                evidence_pack, strategy, explanation = self._stage_strategy_generation(
                    context, entity, signals, risk_result
                )
                # Ensure strategy is a dict before calling .get()
                if isinstance(strategy, dict):
                    action_count = len(strategy.get('actions', []))
                else:
                    logger.warning(f"Strategy is not a dict: {type(strategy)}")
                    action_count = 0
                    strategy = {}
                debug_print(f"Generated {action_count} strategic actions", "StrategyPlanner", "receive")
                context.stages_completed.append("strategy_generation")
            else:
                debug_print("LLM agents skipped (--skip-llm flag)", "CaseManager", "info")
            
            # Stage 7: Quality Assurance
            logger.info(f"[{context.case_id}] Stage 7: Quality Assurance")
            debug_print("Running QA validation...", "CriticQA", "send")
            response = self._stage_qa_and_assembly(
                context, entity, signals, risk_result, strategy, explanation, freshness
            )
            debug_print(f"QA status: {response.get('audit', {}).get('qa_status', 'unknown')}", "CriticQA", "receive")
            context.stages_completed.append("quality_assurance")
            
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            debug_print(f"Pipeline completed in {duration_ms:.0f}ms ✓", "CaseManager", "info")
            
            return PipelineResult(
                success=True,
                response=response,
                context=context,
                duration_ms=duration_ms,
            )
            
        except Exception as e:
            logger.error(f"[{context.case_id}] Pipeline failed: {e}")
            debug_print(f"Pipeline FAILED: {e}", "CaseManager", "error")
            context.errors.append({
                "stage": context.stages_completed[-1] if context.stages_completed else "init",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            })
            
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            return PipelineResult(
                success=False,
                response=self._build_error_response(context, str(e)),
                context=context,
                duration_ms=duration_ms,
            )
    
    def _stage_data_acquisition(
        self,
        context: CaseContext
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Stage 1: Parallel data acquisition from all sources"""
        signals = {}
        registry_data = {}
        
        # Fetch business_registry first so we can obtain a canonical
        # location (lat/lon) to pass to spatial queries for other agents.
        debug_print("Fetching business_registry first to obtain location...", "DataAcquisition", "info")
        try:
            # Pass full query with name and address to get best matching
            # The business_registry_agent will extract street number for matching
            search_query = context.business_query  # Use full original query for best matching
            biz_result = self.business_registry_agent.fetch_signals(
                business_name=search_query,
                as_of=context.as_of,
            )
            if hasattr(biz_result, 'to_dict'):
                result_dict = biz_result.to_dict()
            elif hasattr(biz_result, 'signals'):
                result_dict = biz_result.signals
                result_dict['evidence_refs'] = getattr(biz_result, 'evidence_refs', [])
                result_dict['data_gaps'] = getattr(biz_result, 'data_gaps', [])
            else:
                result_dict = biz_result if isinstance(biz_result, dict) else {}
            signals['business_registry'] = result_dict
            registry_data = result_dict
            # candidates may be at top level or under 'signals' key depending on agent output format
            candidates = result_dict.get('candidates', []) or result_dict.get('signals', {}).get('candidates', [])
            record_count = len(candidates)
            # Debug: log primary candidate if found
            primary = result_dict.get('primary') or result_dict.get('signals', {}).get('primary')
            if primary:
                logger.info(f"Primary business match: {primary.get('business_name')} at {primary.get('address')}")
                # Update context if we found a good match to help other agents
                if not context.business_address and primary.get('address'):
                    context.business_address = primary.get('address')
            debug_print(f"business_registry returned (records/count: {record_count})", "business_registry", "receive")
        except Exception as e:
            logger.warning(f"business_registry agent failed: {e}")
            debug_print(f"business_registry FAILED: {e}", "business_registry", "error")
            context.warnings.append(f"Failed to fetch business_registry: {str(e)}")
            signals['business_registry'] = {"signals": {"candidates": [], "primary": None}, "evidence_refs": [], "data_gaps": [str(e)], "freshness": None}

        # Extract lat/lon from primary registry candidate if available.
        # Support multiple formats:
        # - direct fields: 'latitude' / 'longitude' or 'lat' / 'lon'
        # - nested business_location with latitude/longitude
        # - GeoJSON style 'location' or 'business_location' with 'coordinates' [lon, lat]
        lat = None
        lon = None
        try:
            # primary may be directly in business_registry or under signals subkey
            biz_reg = signals.get('business_registry', {})
            primary = biz_reg.get('primary') or biz_reg.get('signals', {}).get('primary')
            if primary and isinstance(primary, dict):
                # Try direct numeric/string fields first
                lat_val = None
                lon_val = None
                # top-level latitude/longitude or lat/lon
                if 'latitude' in primary or 'longitude' in primary or 'lat' in primary or 'lon' in primary:
                    lat_val = primary.get('latitude') or primary.get('lat')
                    lon_val = primary.get('longitude') or primary.get('lon')

                # nested business_location object may also contain latitude/longitude
                if (lat_val is None or lon_val is None) and isinstance(primary.get('business_location'), dict):
                    bl = primary.get('business_location')
                    lat_val = lat_val or bl.get('latitude') or bl.get('lat')
                    lon_val = lon_val or bl.get('longitude') or bl.get('lon')

                # If we have lat/lon values, coerce to float
                if lat_val is not None and lon_val is not None:
                    try:
                        lat = float(lat_val)
                        lon = float(lon_val)
                    except Exception:
                        lat = None
                        lon = None

                # Fallback to GeoJSON style coordinates: [lon, lat]
                if lat is None or lon is None:
                    loc = primary.get('location') or primary.get('business_location')
                    if loc and isinstance(loc, dict):
                        coords = loc.get('coordinates')
                        if coords and isinstance(coords, (list, tuple)) and len(coords) >= 2:
                            try:
                                lon, lat = float(coords[0]), float(coords[1])
                            except Exception:
                                lat = None
                                lon = None
        except Exception:
            lat = None
            lon = None

        # Also try to extract neighborhood from registry primary for agents that require area
        neighborhood = None
        try:
            biz_reg = signals.get('business_registry', {})
            primary = biz_reg.get('primary') or biz_reg.get('signals', {}).get('primary')
            if primary and isinstance(primary, dict):
                neighborhood = primary.get('neighborhood') or primary.get('area') or None
        except Exception:
            neighborhood = None

        # If exact primary lat/lon not available, try to find the nearest candidate
        if lat is None or lon is None:
            try:
                biz_reg = signals.get('business_registry', {})
                candidates = biz_reg.get('candidates', []) or biz_reg.get('signals', {}).get('candidates', []) or []
                # collect candidates that have lat/lon in a variety of fields
                cand_coords = []
                for c in candidates:
                    if not isinstance(c, dict):
                        continue
                    # try multiple possible lat/lon encodings
                    lat_val = c.get('latitude') or c.get('lat')
                    lon_val = c.get('longitude') or c.get('lon')
                    if (lat_val is None or lon_val is None) and isinstance(c.get('business_location'), dict):
                        bl = c.get('business_location')
                        lat_val = lat_val or bl.get('latitude') or bl.get('lat')
                        lon_val = lon_val or bl.get('longitude') or bl.get('lon')
                    # geojson style
                    if (lat_val is None or lon_val is None) and (c.get('location') or c.get('business_location')):
                        loc = c.get('location') or c.get('business_location')
                        if isinstance(loc, dict):
                            coords = loc.get('coordinates')
                            if coords and isinstance(coords, (list, tuple)) and len(coords) >= 2:
                                try:
                                    lon_val, lat_val = float(coords[0]), float(coords[1])
                                except Exception:
                                    pass
                    try:
                        if lat_val is not None and lon_val is not None:
                            cand_coords.append((float(lat_val), float(lon_val), c))
                    except Exception:
                        continue

                chosen = None
                # Try to geocode the provided address to pick the nearest candidate
                target_lat = None
                target_lon = None
                try:
                    norm = self.address_normalize_agent.normalize(context.business_address or context.business_query)
                    norm_str = norm.to_dict().get('normalized') if hasattr(norm, 'to_dict') else (norm.get('normalized') if isinstance(norm, dict) else None)
                    geo_res = self.geo_resolve_agent.resolve(norm_str or (context.business_address or context.business_query))
                    geo = geo_res.to_dict() if hasattr(geo_res, 'to_dict') else geo_res
                    target_lat = float(geo.get('lat')) if geo and geo.get('lat') else None
                    target_lon = float(geo.get('lon')) if geo and geo.get('lon') else None
                except Exception:
                    target_lat = None
                    target_lon = None

                if cand_coords:
                    if target_lat is not None and target_lon is not None:
                        # pick candidate with minimum haversine distance
                        best = min(cand_coords, key=lambda t: _haversine_km(target_lat, target_lon, t[0], t[1]))
                        chosen = best
                    else:
                        # no geocode target available - pick first candidate with coords
                        chosen = cand_coords[0]

                if chosen:
                    lat, lon = float(chosen[0]), float(chosen[1])
                    debug_print(f"No primary coords; using nearest registry candidate at ({lat}, {lon})", "CaseManager", "info")
                else:
                    debug_print("No candidate coordinates available to use as fallback.", "CaseManager", "info")
            except Exception as e:
                debug_print(f"Nearest-candidate fallback failed: {e}", "CaseManager", "error")

        # Build remaining data tasks and provide lat/lon/neighborhood for spatial or area queries
        common_kwargs = {"lat": lat, "lon": lon, "address": context.business_address or context.business_query, "neighborhood": neighborhood, "as_of": context.as_of}
        data_tasks = [
            ("permits", self.permits_agent.fetch_signals, dict(common_kwargs)),
            ("complaints_311", self.complaints_311_agent.fetch_signals, dict(common_kwargs)),
            ("dbi_complaints", self.dbi_complaints_agent.fetch_signals, dict(common_kwargs)),
            ("sfpd_incidents", self.sfpd_incidents_agent.fetch_signals, dict(common_kwargs)),
            ("evictions", self.evictions_agent.fetch_signals, dict(common_kwargs)),
            ("vacancy", self.vacancy_agent.fetch_signals, dict(common_kwargs)),
        ]

        debug_print(f"Launching {len(data_tasks)} data agents in parallel (with lat/lon: {lat is not None})", "DataAcquisition", "info")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_task = {
                executor.submit(task_func, **task_kwargs): task_name
                for task_name, task_func, task_kwargs in data_tasks
            }

            for future in as_completed(future_to_task):
                task_name = future_to_task[future]
                try:
                    debug_print(f"Fetching {task_name}...", task_name, "send")
                    result = future.result()
                    if hasattr(result, 'to_dict'):
                        result_dict = result.to_dict()
                    elif hasattr(result, 'signals'):
                        result_dict = result.signals
                        result_dict['evidence_refs'] = getattr(result, 'evidence_refs', [])
                        result_dict['data_gaps'] = getattr(result, 'data_gaps', [])
                    else:
                        result_dict = result if isinstance(result, dict) else {}

                    # friendly debug count: try dataset-specific count keys
                    # Signals might be at top level or under 'signals' key
                    signals_data = result_dict.get('signals', result_dict)
                    if isinstance(signals_data, dict):
                        # Try multiple key patterns for count
                        prefix = task_name.split("_")[0]
                        record_count = (
                            signals_data.get(f'{prefix}_count_6m', 0) or
                            signals_data.get(f'{prefix}_count_12m', 0) or
                            signals_data.get('permit_count_6m', 0) or
                            signals_data.get('complaint_count_6m', 0) or
                            signals_data.get('incident_count_6m', 0) or
                            signals_data.get('dbi_count_6m', 0) or
                            len(signals_data.get('records', [])) or
                            0
                        )
                    else:
                        record_count = 0
                    debug_print(f"{task_name} returned (records/count: {record_count})", task_name, "receive")

                    signals[task_name] = result_dict
                except Exception as e:
                    logger.warning(f"Data agent {task_name} failed: {e}")
                    debug_print(f"{task_name} FAILED: {e}", task_name, "error")
                    context.warnings.append(f"Failed to fetch {task_name}: {str(e)}")
                    signals[task_name] = {"error": str(e), "data_gaps": [f"{task_name} unavailable"]}

        return signals, registry_data
    
    def _stage_entity_resolution(
        self,
        context: CaseContext,
        registry_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Stage 2: Resolve and normalize business entity"""
        # Normalize address
        normalized_result = self.address_normalize_agent.normalize(context.business_query)
        # Convert to dict if it's a dataclass
        normalized = normalized_result.to_dict() if hasattr(normalized_result, 'to_dict') else normalized_result
        
        # Get geo coordinates if needed
        geo_result = None
        registry_lat = registry_data.get("lat") if isinstance(registry_data, dict) else getattr(registry_data, 'lat', None)
        registry_lon = registry_data.get("lon") if isinstance(registry_data, dict) else getattr(registry_data, 'lon', None)
        
        if not registry_lat or not registry_lon:
            normalized_addr = normalized.get("normalized", context.business_query) if isinstance(normalized, dict) else context.business_query
            geo_raw = self.geo_resolve_agent.resolve(normalized_addr)
            geo_result = geo_raw.to_dict() if hasattr(geo_raw, 'to_dict') else geo_raw
        
        # Get registry candidates (primary business info)
        registry_candidates = []
        if isinstance(registry_data, dict):
            candidates = registry_data.get("signals", {}).get("candidates", [])
            if candidates:
                registry_candidates = candidates
        
        # Resolve entity
        entity_raw = self.entity_resolver_agent.resolve(
            business_name=context.business_query,
            address=normalized.get("normalized", context.business_query) if isinstance(normalized, dict) else context.business_query,
            lat=geo_result.get("lat") if geo_result else None,
            lon=geo_result.get("lon") if geo_result else None,
            registry_candidates=registry_candidates,
        )
        # Convert to dict if it's a dataclass
        entity = entity_raw.to_dict() if hasattr(entity_raw, 'to_dict') else entity_raw
        
        return entity
    
    def _stage_feature_building(
        self,
        context: CaseContext,
        signals: Dict[str, Any],
        entity: Dict[str, Any]
    ) -> Any:  # Returns ModelFeatures object (not dict)
        """Stage 3: Build model features from signals"""
        # FeatureBuilderAgent expects entity_id (str), signals, as_of
        entity_id = entity.get("matched_id") or entity.get("business_id") or context.case_id
        features = self.feature_builder_agent.build_features(
            entity_id=entity_id,
            signals=signals,
            as_of=context.as_of,
        )
        # Return ModelFeatures object directly - RiskModelAgent needs it
        return features
    
    def _stage_risk_scoring(
        self,
        context: CaseContext,
        features: Any  # ModelFeatures object
    ) -> Dict[str, Any]:
        """Stage 4: Run risk model"""
        risk_result = self.risk_model_agent.predict(features)
        # Convert RiskScore to dict
        if hasattr(risk_result, 'to_dict'):
            return risk_result.to_dict()
        return risk_result
    
    def _stage_freshness_check(
        self,
        context: CaseContext,
        signals: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Stage 5: Check data freshness"""
        # Extract timestamps from signals - each signal dict may have a 'fetched_at' or 'timestamp' field
        pulled_timestamps = {}
        for key, signal_data in signals.items():
            if isinstance(signal_data, dict):
                ts = signal_data.get("fetched_at") or signal_data.get("timestamp")
                if ts:
                    if isinstance(ts, str):
                        try:
                            pulled_timestamps[key] = datetime.fromisoformat(ts)
                        except:
                            pass
                    elif isinstance(ts, datetime):
                        pulled_timestamps[key] = ts
            # If no timestamps, default to now
            if key not in pulled_timestamps:
                pulled_timestamps[key] = context.as_of
        
        freshness = self.data_freshness_agent.check_all_freshness(
            pulled_timestamps=pulled_timestamps,
            as_of=context.as_of,
        )
        # Convert to dict if needed
        if hasattr(freshness, 'to_dict'):
            return freshness.to_dict()
        return freshness
    
    def _stage_strategy_generation(
        self,
        context: CaseContext,
        entity: Dict[str, Any],
        signals: Dict[str, Any],
        risk_result: Dict[str, Any]
    ) -> Tuple[Any, Dict[str, Any], Dict[str, Any]]:
        """Stage 6: Generate strategy using LLM agents"""
        print(f"[DEBUG] _stage_strategy_generation called")
        print(f"[DEBUG] entity type: {type(entity)}, is dict: {isinstance(entity, dict)}")
        print(f"[DEBUG] signals type: {type(signals)}, is dict: {isinstance(signals, dict)}")
        print(f"[DEBUG] risk_result type: {type(risk_result)}, is dict: {isinstance(risk_result, dict)}")
        if isinstance(risk_result, dict):
            print(f"[DEBUG] risk_result keys: {list(risk_result.keys())}")
            print(f"[DEBUG] risk_result top_drivers type: {type(risk_result.get('top_drivers', 'N/A'))}")
        if isinstance(signals, dict):
            for k, v in signals.items():
                print(f"[DEBUG] signals[{k}] type: {type(v)}")
        
        # Package evidence
        print(f"[DEBUG] Calling evidence_packager_agent.package...")
        evidence_pack = self.evidence_packager_agent.package(
            entity=entity,
            signals=signals,
            risk_result=risk_result,
            as_of=context.as_of,
            horizon_months=context.horizon_months,
        )
        print(f"[DEBUG] Evidence pack type: {type(evidence_pack)}")
        
        # Generate explanation
        explanation = {}
        try:
            print(f"[DEBUG] Calling explanation_agent.explain...")
            explanation = self.explanation_agent.explain(evidence_pack)
            print(f"[DEBUG] Explanation type: {type(explanation)}")
        except Exception as e:
            logger.warning(f"Explanation generation failed: {e}")
            context.warnings.append(f"Explanation unavailable: {str(e)}")
        
        # Generate strategy
        strategy = {}
        try:
            print(f"[DEBUG] Calling strategy_planner_agent.plan...")
            strategy = self.strategy_planner_agent.plan(
                evidence_pack,
                focus_areas=context.options.get("focus_areas"),
            )
            print(f"[DEBUG] Strategy type: {type(strategy)}, is dict: {isinstance(strategy, dict)}")
        except Exception as e:
            logger.warning(f"Strategy generation failed: {e}")
            context.warnings.append(f"Strategy unavailable: {str(e)}")
        
        print(f"[DEBUG] _stage_strategy_generation returning")
        return evidence_pack, strategy, explanation
    
    def _stage_qa_and_assembly(
        self,
        context: CaseContext,
        entity: Dict[str, Any],
        signals: Dict[str, Any],
        risk_result: Dict[str, Any],
        strategy: Dict[str, Any],
        explanation: Dict[str, Any],
        freshness: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Stage 7: Quality assurance and final assembly"""
        # Build response
        response = {
            "case_id": context.case_id,
            "as_of": context.as_of.isoformat(),
            "horizon_months": context.horizon_months,
            "entity": {
                "entity_id": entity.get("entity_id", "unknown"),
                "business_name": entity.get("business_name", ""),
                "address": entity.get("address", ""),
                "neighborhood": entity.get("neighborhood", ""),
                "match_confidence": entity.get("match_confidence", 0.0),
            },
            "risk": {
                "score": risk_result.get("score", 0.0),
                "band": risk_result.get("band", "medium"),
                "model_version": risk_result.get("model_version", "unknown"),
                "top_drivers": risk_result.get("top_drivers", []),
            },
            "signals": {
                k: v for k, v in signals.items() 
                if not isinstance(v, dict) or "error" not in v
            },
            "strategy": strategy,
            "explanation": explanation,
            "limitations": [],
            "audit": {
                "data_pulled_at": datetime.now().isoformat(),
                "dataset_versions": freshness.get("checks", []) if isinstance(freshness, dict) else [],
                "agent_versions": self._get_agent_versions(),
                "qa_status": "PENDING",
            },
        }
        
        # Run QA validation
        qa_result = self.critic_qa_agent.validate(response)
        response["audit"]["qa_status"] = qa_result.get("status", "UNKNOWN")
        
        if qa_result.get("status") == "FAIL":
            # Apply patches
            response = self.critic_qa_agent.patch(response, qa_result.get("patch_plan", []))
            context.warnings.append("QA validation failed - patches applied")
        
        # Run policy guard
        policy_result = self.policy_guard_agent.validate(response, content_type="compliance")
        if not policy_result.get("is_valid"):
            response = self.policy_guard_agent.add_disclaimers(response, content_type="compliance")
            context.warnings.extend([
                f"Policy issue: {v.get('issue')}" for v in policy_result.get("violations", [])
            ])
        
        # Add warnings as limitations
        response["limitations"].extend(context.warnings)
        
        return response
    
    def _parse_business_query(self, query: str) -> Dict[str, str]:
        """
        Parse business query to separate business name from address.
        
        Expected formats:
        - "Business Name, Address"
        - "Business Name"
        - "Address"
        """
        query = query.strip()
        
        # Look for comma separator
        if "," in query:
            parts = query.split(",", 1)  # Split on first comma only
            business_name = parts[0].strip()
            address = parts[1].strip()
            return {"business_name": business_name, "address": address}
        
        # No comma - try to guess based on content
        # If it looks like an address (contains numbers), treat as address
        if re.search(r'\d+', query):
            return {"business_name": None, "address": query}
        else:
            return {"business_name": query, "address": None}

    def _build_error_response(
        self,
        context: CaseContext,
        error_message: str
    ) -> Dict[str, Any]:
        """Build error response when pipeline fails"""
        return {
            "case_id": context.case_id,
            "as_of": context.as_of.isoformat(),
            "horizon_months": context.horizon_months,
            "entity": {
                "entity_id": "unknown",
                "business_name": context.business_query,
                "address": "",
                "neighborhood": "",
                "match_confidence": 0.0,
            },
            "risk": {
                "score": 0.0,
                "band": "unknown",
                "model_version": "error",
                "top_drivers": [],
            },
            "signals": {},
            "strategy": {
                "summary": "Analysis could not be completed",
                "actions": [],
                "questions_for_user": ["Please verify the business name and address"],
            },
            "limitations": [
                f"Analysis failed: {error_message}",
                f"Completed stages: {', '.join(context.stages_completed) or 'none'}",
            ],
            "audit": {
                "data_pulled_at": datetime.now().isoformat(),
                "qa_status": "ERROR",
                "errors": context.errors,
            },
        }
    
    def _get_agent_versions(self) -> List[Dict[str, str]]:
        """Get versions of all agents"""
        return [
            {"agent": "CaseManagerAgent", "version": self.VERSION},
            {"agent": "EvidencePackagerAgent", "version": self.evidence_packager_agent.get_version()},
            {"agent": "ExplanationAgent", "version": self.explanation_agent.get_version()},
            {"agent": "StrategyPlannerAgent", "version": self.strategy_planner_agent.get_version()},
            {"agent": "CriticQAAgent", "version": self.critic_qa_agent.get_version()},
            {"agent": "PolicyGuardAgent", "version": self.policy_guard_agent.get_version()},
            {"agent": "RiskModelAgent", "version": self.risk_model_agent.get_version()},
        ]
    
    def get_version(self) -> str:
        """Return agent version"""
        return self.VERSION


# Convenience function for simple usage
def analyze_business(
    business_query: str,
    horizon_months: int = 6,
    **options
) -> Dict[str, Any]:
    """
    Convenience function to run a complete risk analysis.
    
    Args:
        business_query: Business name and/or address
        horizon_months: Forecast horizon
        **options: Additional options
        
    Returns:
        Complete RiskAnalysisResponse
    """
    manager = CaseManagerAgent()
    result = manager.analyze(
        business_query=business_query,
        horizon_months=horizon_months,
        options=options,
    )
    return result.response
