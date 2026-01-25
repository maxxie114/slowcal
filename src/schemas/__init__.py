"""
JSON Schemas for agent outputs

Provides importable schemas and validation utilities.
"""

import json
from pathlib import Path
from typing import Dict, Any

SCHEMA_DIR = Path(__file__).parent


def load_schema(schema_name: str) -> Dict[str, Any]:
    """Load a JSON schema by name"""
    schema_path = SCHEMA_DIR / f"{schema_name}.json"
    with open(schema_path) as f:
        return json.load(f)


def get_risk_analysis_schema() -> Dict[str, Any]:
    """Get the RiskAnalysisResponse schema"""
    return load_schema("risk_analysis_response")


def get_evidence_pack_schema() -> Dict[str, Any]:
    """Get the EvidencePack schema"""
    return load_schema("evidence_pack")
