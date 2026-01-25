"""
Schema Validation for Agent Outputs

Provides Pydantic models and JSON Schema validation for:
- RiskAnalysisResponse (final output)
- EvidencePack (LLM context)
- Intermediate agent outputs

Ensures contract-first approach with strict type checking.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class RiskBand(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Direction(str, Enum):
    UP = "up"
    DOWN = "down"
    STABLE = "stable"


class ActionHorizon(str, Enum):
    TWO_WEEKS = "2_weeks"
    SIXTY_DAYS = "60_days"
    SIX_MONTHS = "6_months"


class Effort(str, Enum):
    LOW = "low"
    MEDIUM = "med"
    HIGH = "high"


class Impact(str, Enum):
    LOW = "low"
    MEDIUM = "med"
    HIGH = "high"


class QAStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class JoinStrategy(str, Enum):
    EXACT_ADDRESS = "exact_address"
    SPATIAL_RADIUS = "spatial_radius"
    NEIGHBORHOOD_AGGREGATE = "neighborhood_aggregate"


# =============================================================================
# EVIDENCE MODELS
# =============================================================================

class EvidenceRef(BaseModel):
    """Reference to a piece of evidence"""
    id: str = Field(..., description="Unique evidence ID (e.g., 'e:311-001')")
    dataset_id: Optional[str] = None
    pulled_at: Optional[datetime] = None
    summary: Optional[str] = None


class DatasetVersion(BaseModel):
    """Dataset pull metadata"""
    dataset_id: str
    pulled_at: datetime


class SignalValue(BaseModel):
    """A single signal value with evidence"""
    value: Union[int, float, str]
    period: Optional[str] = None  # e.g., "3m", "6m", "12m"
    evidence_refs: List[str] = Field(default_factory=list)


class SignalSet(BaseModel):
    """Set of signals from a data source"""
    count_3m: Optional[int] = None
    count_6m: Optional[int] = None
    count_12m: Optional[int] = None
    trend: Optional[Direction] = None
    top_categories: Optional[List[str]] = None
    data_gaps: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)


# =============================================================================
# ENTITY MODELS
# =============================================================================

class ResolvedEntity(BaseModel):
    """Resolved business entity with location"""
    entity_id: str
    business_name: str
    address: str
    neighborhood: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    match_confidence: float = Field(..., ge=0.0, le=1.0)
    join_strategy: Optional[JoinStrategy] = None


# =============================================================================
# RISK MODELS
# =============================================================================

class RiskDriver(BaseModel):
    """A top risk driver with evidence"""
    driver: str
    direction: Direction
    contribution: Optional[float] = None
    evidence_refs: List[str] = Field(default_factory=list)


class RiskResult(BaseModel):
    """Risk scoring result"""
    score: float = Field(..., ge=0.0, le=1.0)
    band: RiskBand
    model_version: str
    top_drivers: List[RiskDriver] = Field(default_factory=list)


# =============================================================================
# STRATEGY MODELS
# =============================================================================

class StrategyAction(BaseModel):
    """A single strategy action"""
    horizon: ActionHorizon
    action: str
    why: str
    expected_impact: Impact
    effort: Effort
    evidence_refs: List[str] = Field(default_factory=list)
    success_metric: Optional[str] = None


class StrategyPlan(BaseModel):
    """Complete strategy plan"""
    summary: str
    actions: List[StrategyAction] = Field(default_factory=list)
    questions_for_user: List[str] = Field(default_factory=list)
    
    @field_validator('actions')
    @classmethod
    def validate_evidence_coverage(cls, v):
        """Warn if actions lack evidence refs"""
        for action in v:
            if not action.evidence_refs:
                logger.warning(f"Action '{action.action[:50]}...' lacks evidence refs")
        return v


# =============================================================================
# SIGNALS MODELS
# =============================================================================

class AllSignals(BaseModel):
    """All signals from data agents"""
    permits: Optional[SignalSet] = None
    complaints_311: Optional[SignalSet] = None
    dbi: Optional[SignalSet] = None
    sfpd: Optional[SignalSet] = None
    evictions: Optional[SignalSet] = None
    vacancy: Optional[SignalSet] = None


# =============================================================================
# AUDIT MODELS
# =============================================================================

class AgentVersion(BaseModel):
    """Agent version tracking"""
    agent: str
    version: str


class AuditInfo(BaseModel):
    """Audit trail for reproducibility"""
    data_pulled_at: datetime
    dataset_versions: List[DatasetVersion] = Field(default_factory=list)
    agent_versions: List[AgentVersion] = Field(default_factory=list)
    qa_status: QAStatus


# =============================================================================
# MAIN OUTPUT SCHEMA
# =============================================================================

class RiskAnalysisResponse(BaseModel):
    """
    Complete risk analysis response.
    
    This is the final output schema for the multi-agent pipeline.
    All fields are validated for type correctness and evidence coverage.
    """
    case_id: str
    as_of: datetime
    horizon_months: int = Field(default=6, ge=1, le=24)
    
    entity: ResolvedEntity
    risk: RiskResult
    signals: AllSignals
    strategy: StrategyPlan
    
    limitations: List[str] = Field(default_factory=list)
    audit: AuditInfo
    
    @model_validator(mode='after')
    def validate_evidence_chain(self):
        """Validate that strategy references existing evidence"""
        # Collect all evidence refs from signals
        available_refs = set()
        
        if self.signals.permits:
            available_refs.update(self.signals.permits.evidence_refs)
        if self.signals.complaints_311:
            available_refs.update(self.signals.complaints_311.evidence_refs)
        if self.signals.dbi:
            available_refs.update(self.signals.dbi.evidence_refs)
        if self.signals.sfpd:
            available_refs.update(self.signals.sfpd.evidence_refs)
        if self.signals.evictions:
            available_refs.update(self.signals.evictions.evidence_refs)
        if self.signals.vacancy:
            available_refs.update(self.signals.vacancy.evidence_refs)
        
        # Add risk driver refs
        for driver in self.risk.top_drivers:
            available_refs.update(driver.evidence_refs)
        
        # Check strategy refs (warn only, don't fail)
        for action in self.strategy.actions:
            for ref in action.evidence_refs:
                if ref not in available_refs and not ref.startswith("e:"):
                    logger.warning(f"Strategy ref '{ref}' not found in signals")
        
        return self
    
    def to_json_schema(self) -> Dict[str, Any]:
        """Get JSON schema for this model"""
        return self.model_json_schema()


# =============================================================================
# EVIDENCE PACK (LLM Context)
# =============================================================================

class EvidencePack(BaseModel):
    """
    Compact evidence package for LLM context.
    
    Contains only what the LLM needs to generate grounded responses.
    """
    entity_summary: str
    risk_score: float
    risk_band: RiskBand
    top_drivers: List[RiskDriver]
    
    # Key signals (summarized)
    signal_summaries: Dict[str, str] = Field(default_factory=dict)
    
    # Evidence snippets with IDs
    evidence_items: List[Dict[str, str]] = Field(default_factory=list)
    
    # Uncertainty and gaps
    data_gaps: List[str] = Field(default_factory=list)
    confidence_notes: List[str] = Field(default_factory=list)
    
    # Time context
    as_of: datetime
    horizon_months: int


# =============================================================================
# VALIDATION HELPERS
# =============================================================================

class ValidationError(Exception):
    """Raised when schema validation fails"""
    def __init__(self, message: str, errors: List[Dict[str, Any]] = None):
        super().__init__(message)
        self.errors = errors or []


def validate_schema(
    data: Dict[str, Any],
    schema_class: type,
) -> BaseModel:
    """
    Validate data against a Pydantic schema.
    
    Args:
        data: Dictionary to validate
        schema_class: Pydantic model class
    
    Returns:
        Validated model instance
    
    Raises:
        ValidationError: If validation fails
    """
    try:
        return schema_class.model_validate(data)
    except Exception as e:
        errors = []
        if hasattr(e, 'errors'):
            errors = e.errors()
        raise ValidationError(f"Schema validation failed: {e}", errors)


def validate_json_string(
    json_string: str,
    schema_class: type,
) -> BaseModel:
    """
    Validate JSON string against a Pydantic schema.
    
    Args:
        json_string: JSON string to validate
        schema_class: Pydantic model class
    
    Returns:
        Validated model instance
    """
    import json
    try:
        data = json.loads(json_string)
        return validate_schema(data, schema_class)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON: {e}")


def get_schema_json(schema_class: type) -> Dict[str, Any]:
    """Get JSON schema for a Pydantic model"""
    return schema_class.model_json_schema()


class SchemaValidator:
    """
    Schema validator class for agent outputs.
    
    Provides convenient validation methods with error details.
    
    Example:
        validator = SchemaValidator()
        is_valid, errors = validator.validate(data, schema)
    """
    
    def __init__(self):
        self._cache = {}
    
    def validate(
        self,
        data: Dict[str, Any],
        schema: Any,
    ) -> tuple:
        """
        Validate data against a schema.
        
        Args:
            data: Dictionary to validate
            schema: Either a Pydantic model class or JSON Schema dict
            
        Returns:
            Tuple of (is_valid: bool, errors: List[str])
        """
        errors = []
        
        try:
            if isinstance(schema, type) and issubclass(schema, BaseModel):
                # Pydantic model
                schema.model_validate(data)
            elif isinstance(schema, dict):
                # JSON Schema - basic validation
                errors = self._validate_json_schema(data, schema)
                if errors:
                    return False, errors
            return True, []
        except Exception as e:
            if hasattr(e, 'errors'):
                for err in e.errors():
                    loc = ".".join(str(x) for x in err.get("loc", []))
                    msg = err.get("msg", str(err))
                    errors.append(f"{loc}: {msg}")
            else:
                errors.append(str(e))
            return False, errors
    
    def _validate_json_schema(
        self,
        data: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> List[str]:
        """Basic JSON Schema validation"""
        errors = []
        
        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Check properties
        properties = schema.get("properties", {})
        for field, field_schema in properties.items():
            if field in data:
                value = data[field]
                field_type = field_schema.get("type")
                
                # Type checking
                type_map = {
                    "string": str,
                    "number": (int, float),
                    "integer": int,
                    "boolean": bool,
                    "array": list,
                    "object": dict,
                }
                
                expected_type = type_map.get(field_type)
                if expected_type and not isinstance(value, expected_type):
                    errors.append(f"{field}: expected {field_type}, got {type(value).__name__}")
                
                # Enum checking
                enum_values = field_schema.get("enum")
                if enum_values and value not in enum_values:
                    errors.append(f"{field}: must be one of {enum_values}")
        
        return errors
    
    def validate_response(self, data: Dict[str, Any]) -> tuple:
        """Validate against RiskAnalysisResponse schema"""
        return self.validate(data, RiskAnalysisResponse)
    
    def validate_evidence_pack(self, data: Dict[str, Any]) -> tuple:
        """Validate against EvidencePack schema"""
        return self.validate(data, EvidencePack)
