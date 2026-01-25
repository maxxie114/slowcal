"""
Explanation Agent (Nemotron)

Converts top risk drivers and evidence into plain-language explanations.
Outputs structured JSON with "what changed", "why it matters", "what to monitor".

Uses Nemotron via NIM for natural language generation.
"""

import logging
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Import path handling
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.nim_client import NIMClient
from tools.schema_validation import SchemaValidator
from .evidence_packager_agent import EvidencePack


# Output schema for explanation
EXPLANATION_SCHEMA = {
    "type": "object",
    "required": ["what_changed", "why_it_matters", "what_to_monitor"],
    "properties": {
        "what_changed": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["change", "evidence_refs"],
                "properties": {
                    "change": {"type": "string"},
                    "timeframe": {"type": "string"},
                    "evidence_refs": {"type": "array", "items": {"type": "string"}}
                }
            }
        },
        "why_it_matters": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["insight", "impact"],
                "properties": {
                    "insight": {"type": "string"},
                    "impact": {"type": "string", "enum": ["positive", "negative", "neutral"]},
                    "evidence_refs": {"type": "array", "items": {"type": "string"}}
                }
            }
        },
        "what_to_monitor": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["metric", "reason"],
                "properties": {
                    "metric": {"type": "string"},
                    "reason": {"type": "string"},
                    "threshold": {"type": "string"},
                    "evidence_refs": {"type": "array", "items": {"type": "string"}}
                }
            }
        },
        "summary": {"type": "string"},
        "limitations": {"type": "array", "items": {"type": "string"}}
    }
}

EXPLANATION_PROMPT_TEMPLATE = """You are an expert business risk analyst explaining risk factors to a small business owner.

Given the following evidence pack for a business risk analysis, provide a clear explanation in JSON format.

## Business Context
{entity_summary}

## Risk Score
Score: {risk_score:.2f} ({risk_band} risk)
Analysis horizon: {horizon_months} months

## Top Risk Drivers
{drivers_text}

## Signal Summaries
{signals_text}

## Evidence Items
{evidence_text}

## Data Gaps
{data_gaps_text}

## Instructions
Generate a JSON response with these sections:
1. "what_changed": Recent changes affecting risk (MUST reference evidence IDs)
2. "why_it_matters": Why these changes impact the business (include impact: positive/negative/neutral)
3. "what_to_monitor": Key metrics to watch going forward
4. "summary": One paragraph executive summary
5. "limitations": Any caveats about the analysis

CRITICAL RULES:
- Every claim MUST include "evidence_refs" array with relevant evidence IDs (e.g., ["e:complaints_311-001"])
- If data is missing, say so explicitly in limitations
- Do not make claims without evidence support
- Use plain language, avoid jargon
- Be specific about timeframes and numbers

Output ONLY valid JSON, no markdown or explanation."""


class ExplanationAgent:
    """
    Agent that generates plain-language risk explanations using Nemotron.
    
    Converts risk drivers and evidence into structured explanations with:
    - What changed (with evidence)
    - Why it matters (with impact assessment)
    - What to monitor (key metrics)
    
    Example:
        agent = ExplanationAgent()
        explanation = agent.explain(evidence_pack)
    """
    
    VERSION = "1.0.0"
    TEMPERATURE = 0.2  # Low temp for consistent explanations
    MAX_TOKENS = 2000
    
    def __init__(self, nim_client: NIMClient = None):
        self.nim_client = nim_client or NIMClient(timeout=300.0)  # 5 min timeout for DGX
        self.validator = SchemaValidator()
    
    def explain(
        self,
        evidence_pack: EvidencePack,
        temperature: float = None,
    ) -> Dict[str, Any]:
        """
        Generate explanation from evidence pack.
        
        Args:
            evidence_pack: Packaged evidence from EvidencePackagerAgent
            temperature: Override default temperature
            
        Returns:
            Structured explanation dict
        """
        # Convert evidence pack to prompt context
        prompt = self._build_prompt(evidence_pack)
        print(f"Explanation Prompt:\n{prompt}\n")  # Debug print
        
        # Call Nemotron
        response = self.nim_client.chat_structured(
            prompt=prompt,
            output_schema=EXPLANATION_SCHEMA,
            temperature=temperature or self.TEMPERATURE,
            max_tokens=self.MAX_TOKENS,
        )
        
        if not response:
            logger.error("Failed to get response from Nemotron")
            return self._fallback_explanation(evidence_pack)
        
        # Parse and validate response
        result = response.parse_json()
        if not result:
            logger.warning("Failed to parse JSON, using fallback")
            return self._fallback_explanation(evidence_pack)
        
        # Validate against schema
        is_valid, errors = self.validator.validate(result, EXPLANATION_SCHEMA)
        if not is_valid:
            logger.warning(f"Schema validation failed: {errors}")
            # Try to fix common issues
            result = self._fix_common_issues(result)
        
        # Add metadata
        result["agent_version"] = self.VERSION
        result["generated_at"] = datetime.now().isoformat()
        
        return result
    
    def _build_prompt(self, evidence_pack: EvidencePack) -> str:
        """Build prompt from evidence pack"""
        pack = evidence_pack.to_dict() if hasattr(evidence_pack, 'to_dict') else evidence_pack
        
        # Format drivers
        drivers_text = ""
        for i, driver in enumerate(pack.get("top_drivers", []), 1):
            d_name = driver.get("driver", "unknown")
            d_dir = driver.get("direction", "stable")
            d_contrib = driver.get("contribution", 0)
            d_refs = ", ".join(driver.get("evidence_refs", []))
            drivers_text += f"{i}. {d_name} ({d_dir}, contribution: {d_contrib:.2f}) - refs: {d_refs}\n"
        
        # Format signals
        signals_text = ""
        for cat, summary in pack.get("signal_summaries", {}).items():
            signals_text += f"- {cat}: {summary}\n"
        
        # Format evidence items
        evidence_text = ""
        for item in pack.get("evidence_items", []):
            eid = item.get("id", "")
            content = item.get("content", "")
            source = item.get("source", "")
            evidence_text += f"- {eid}: {content} (source: {source})\n"
        
        # Format data gaps
        data_gaps_text = "\n".join(f"- {g}" for g in pack.get("data_gaps", [])) or "None identified"
        
        return EXPLANATION_PROMPT_TEMPLATE.format(
            entity_summary=pack.get("entity_summary", "Unknown business"),
            risk_score=pack.get("risk_score", 0.0),
            risk_band=pack.get("risk_band", "medium"),
            horizon_months=pack.get("horizon_months", 6),
            drivers_text=drivers_text or "No drivers identified",
            signals_text=signals_text or "No signals available",
            evidence_text=evidence_text or "No evidence items",
            data_gaps_text=data_gaps_text,
        )
    
    def _fallback_explanation(self, evidence_pack: EvidencePack) -> Dict[str, Any]:
        """Generate fallback explanation when LLM fails"""
        pack = evidence_pack.to_dict() if hasattr(evidence_pack, 'to_dict') else evidence_pack
        
        return {
            "what_changed": [
                {
                    "change": "Risk analysis completed but detailed explanation unavailable",
                    "timeframe": f"Last {pack.get('horizon_months', 6)} months",
                    "evidence_refs": []
                }
            ],
            "why_it_matters": [
                {
                    "insight": f"Current risk level is {pack.get('risk_band', 'unknown')}",
                    "impact": "neutral",
                    "evidence_refs": []
                }
            ],
            "what_to_monitor": [
                {
                    "metric": "Overall risk score",
                    "reason": "Track changes in business risk profile",
                    "evidence_refs": []
                }
            ],
            "summary": f"Business risk score is {pack.get('risk_score', 0):.2f} ({pack.get('risk_band', 'unknown')} risk). Please review the detailed signals for more information.",
            "limitations": [
                "Detailed explanation could not be generated",
                "Review raw signals and evidence for complete picture"
            ],
            "agent_version": self.VERSION,
            "generated_at": datetime.now().isoformat(),
        }
    
    def _fix_common_issues(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Fix common schema validation issues"""
        # Ensure arrays exist
        for key in ["what_changed", "why_it_matters", "what_to_monitor", "limitations"]:
            if key not in result or not isinstance(result[key], list):
                result[key] = []
        
        # Ensure evidence_refs in each item
        for key in ["what_changed", "why_it_matters", "what_to_monitor"]:
            for item in result[key]:
                if "evidence_refs" not in item:
                    item["evidence_refs"] = []
        
        # Ensure impact field
        for item in result.get("why_it_matters", []):
            if "impact" not in item or item["impact"] not in ["positive", "negative", "neutral"]:
                item["impact"] = "neutral"
        
        return result
    
    def get_version(self) -> str:
        """Return agent version"""
        return self.VERSION
