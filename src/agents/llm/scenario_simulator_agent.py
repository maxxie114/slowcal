"""
Scenario Simulator Agent (Nemotron + Deterministic Rules)

Simulates "what-if" scenarios to help business owners understand
potential impacts of changes.

Examples:
- "What if we reduce complaints by 30%?"
- "What if pending permits are resolved?"
- "What if neighborhood vacancy increases?"

This is a planning/education tool - it produces qualitative impact
assessments, not actual re-scoring.
"""

import logging
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


SCENARIO_SCHEMA = {
    "type": "object",
    "required": ["scenario_name", "current_state", "projected_state", "impact_assessment", "implementation_path"],
    "properties": {
        "scenario_name": {"type": "string"},
        "scenario_description": {"type": "string"},
        "current_state": {
            "type": "object",
            "properties": {
                "relevant_signals": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "signal": {"type": "string"},
                            "current_value": {"type": "string"},
                            "evidence_refs": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    }
                },
                "current_risk_score": {"type": "number"},
                "current_risk_band": {"type": "string"}
            }
        },
        "projected_state": {
            "type": "object",
            "properties": {
                "changed_signals": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "signal": {"type": "string"},
                            "projected_value": {"type": "string"},
                            "change_description": {"type": "string"}
                        }
                    }
                },
                "estimated_risk_change": {
                    "type": "string",
                    "enum": ["significant_decrease", "moderate_decrease", "slight_decrease", "no_change", "slight_increase", "moderate_increase", "significant_increase"]
                },
                "confidence": {
                    "type": "string",
                    "enum": ["low", "medium", "high"]
                }
            }
        },
        "impact_assessment": {
            "type": "object",
            "properties": {
                "overall_impact": {
                    "type": "string",
                    "enum": ["very_positive", "positive", "neutral", "negative", "very_negative"]
                },
                "benefits": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "risks": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "trade_offs": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "time_to_impact": {"type": "string"}
            }
        },
        "implementation_path": {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step": {"type": "string"},
                            "effort": {"type": "string"},
                            "timeline": {"type": "string"}
                        }
                    }
                },
                "resources_needed": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "success_indicators": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        },
        "alternative_scenarios": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "relative_impact": {"type": "string"}
                }
            }
        },
        "caveats": {
            "type": "array",
            "items": {"type": "string"}
        }
    }
}

SCENARIO_PROMPT = """You are a business scenario planner helping a small business owner understand the potential impact of changes.

## Business Context
{entity_summary}

## Current Risk Profile
Risk Score: {risk_score:.2f} ({risk_band})
Horizon: {horizon_months} months

## Current Signals
{signals_text}

## Top Risk Drivers
{drivers_text}

## Evidence
{evidence_text}

## Scenario to Analyze
{scenario_description}

## Instructions
Analyze this scenario and produce:

1. "scenario_name": Brief name
2. "scenario_description": What's being changed

3. "current_state":
   - relevant_signals: Current values related to scenario
   - current_risk_score: {risk_score}
   - current_risk_band: "{risk_band}"

4. "projected_state":
   - changed_signals: How signals would change
   - estimated_risk_change: "significant_decrease"/"moderate_decrease"/"slight_decrease"/"no_change"/"slight_increase"/"moderate_increase"/"significant_increase"
   - confidence: "low"/"medium"/"high"

5. "impact_assessment":
   - overall_impact: "very_positive"/"positive"/"neutral"/"negative"/"very_negative"
   - benefits: What improves
   - risks: What could go wrong
   - trade_offs: Considerations
   - time_to_impact: How long until effects seen

6. "implementation_path":
   - steps: Concrete actions to achieve scenario
   - resources_needed: What's required
   - success_indicators: How to measure

7. "alternative_scenarios": Other options to consider

8. "caveats": Important limitations

## CRITICAL RULES
- This is QUALITATIVE impact estimation, not actual prediction
- Reference evidence IDs where relevant
- Be realistic about implementation challenges
- State confidence levels honestly
- Include caveats about model limitations

Output ONLY valid JSON."""


# Pre-defined scenario templates
SCENARIO_TEMPLATES = {
    "reduce_complaints": {
        "name": "Reduce 311 Complaints",
        "prompt_addition": "Scenario: Reduce 311 complaints by 30-50% over the next 6 months through proactive measures.",
    },
    "resolve_permits": {
        "name": "Resolve Pending Permits",
        "prompt_addition": "Scenario: All pending permits are approved and closed within the next 60 days.",
    },
    "address_dbi": {
        "name": "Address DBI Complaints",
        "prompt_addition": "Scenario: All open DBI complaints are resolved and no new complaints filed for 6 months.",
    },
    "neighborhood_decline": {
        "name": "Neighborhood Decline",
        "prompt_addition": "Scenario: Neighborhood vacancy rate increases by 20% and eviction notices increase by 15% over 6 months.",
    },
    "improve_safety": {
        "name": "Improved Safety",
        "prompt_addition": "Scenario: SFPD incidents within 500m radius decrease by 25% over the next year.",
    },
    "custom": {
        "name": "Custom Scenario",
        "prompt_addition": "",  # Will be filled by user
    },
}


class ScenarioSimulatorAgent:
    """
    Agent for simulating business scenarios using Nemotron.
    
    Provides "what-if" analysis for:
    - Complaint reduction scenarios
    - Permit resolution scenarios
    - Neighborhood change scenarios
    - Custom scenarios
    
    This is a planning/education tool that produces qualitative
    impact assessments, not actual re-scoring.
    
    Example:
        agent = ScenarioSimulatorAgent()
        result = agent.simulate(
            evidence_pack=evidence_pack,
            scenario_type="reduce_complaints"
        )
    """
    
    VERSION = "1.0.0"
    TEMPERATURE = 0.3
    MAX_TOKENS = 3000
    
    def __init__(self, nim_client: NIMClient = None):
        self.nim_client = nim_client or NIMClient(timeout=30.0)  # Shorter timeout for testing
        self.validator = SchemaValidator()
    
    def simulate(
        self,
        evidence_pack: EvidencePack,
        scenario_type: str = "custom",
        custom_scenario: str = None,
        temperature: float = None,
    ) -> Dict[str, Any]:
        """
        Simulate a what-if scenario.
        
        Args:
            evidence_pack: Packaged evidence from EvidencePackagerAgent
            scenario_type: Type of scenario (see SCENARIO_TEMPLATES)
            custom_scenario: Custom scenario description (if type="custom")
            temperature: Override default temperature
            
        Returns:
            Structured scenario analysis
        """
        # Get scenario template
        template = SCENARIO_TEMPLATES.get(scenario_type, SCENARIO_TEMPLATES["custom"])
        
        if scenario_type == "custom" and custom_scenario:
            scenario_description = custom_scenario
        else:
            scenario_description = template.get("prompt_addition", "Analyze general business improvement scenario")
        
        # Build prompt
        prompt = self._build_prompt(evidence_pack, scenario_description)
        
        # Call Nemotron
        response = self.nim_client.chat_structured(
            prompt=prompt,
            output_schema=SCENARIO_SCHEMA,
            temperature=temperature or self.TEMPERATURE,
            max_tokens=self.MAX_TOKENS,
        )
        
        if not response:
            logger.error("Failed to get response from Nemotron")
            return self._fallback_scenario(evidence_pack, scenario_description)
        
        # Parse response
        result = response.parse_json()
        if not result:
            logger.warning("Failed to parse JSON, using fallback")
            return self._fallback_scenario(evidence_pack, scenario_description)
        
        # Validate
        is_valid, errors = self.validator.validate(result, SCENARIO_SCHEMA)
        if not is_valid:
            logger.warning(f"Schema validation failed: {errors}")
            result = self._fix_common_issues(result)
        
        # Add standard caveats
        standard_caveats = [
            "This is a qualitative estimation, not a precise prediction",
            "Actual outcomes depend on many factors not captured in the model",
            "Scenario assumes other factors remain constant",
        ]
        result["caveats"] = standard_caveats + result.get("caveats", [])
        
        # Add metadata
        result["agent_version"] = self.VERSION
        result["generated_at"] = datetime.now().isoformat()
        result["scenario_type"] = scenario_type
        
        return result
    
    def list_templates(self) -> Dict[str, str]:
        """List available scenario templates"""
        return {k: v["name"] for k, v in SCENARIO_TEMPLATES.items()}
    
    def _build_prompt(
        self,
        evidence_pack: EvidencePack,
        scenario_description: str
    ) -> str:
        """Build prompt from evidence pack"""
        pack = evidence_pack.to_dict() if hasattr(evidence_pack, 'to_dict') else evidence_pack
        
        # Format drivers
        drivers_text = ""
        for i, driver in enumerate(pack.get("top_drivers", []), 1):
            d_name = driver.get("driver", "unknown")
            d_dir = driver.get("direction", "stable")
            d_refs = ", ".join(driver.get("evidence_refs", []))
            drivers_text += f"{i}. {d_name} ({d_dir}) - refs: {d_refs}\n"
        
        # Format signals
        signals_text = ""
        for cat, summary in pack.get("signal_summaries", {}).items():
            signals_text += f"- {cat}: {summary}\n"
        
        # Format evidence
        evidence_text = ""
        for item in pack.get("evidence_items", []):
            eid = item.get("id", "")
            content = item.get("content", "")
            evidence_text += f"- {eid}: {content}\n"
        
        return SCENARIO_PROMPT.format(
            entity_summary=pack.get("entity_summary", "Unknown business"),
            risk_score=pack.get("risk_score", 0.0),
            risk_band=pack.get("risk_band", "medium"),
            horizon_months=pack.get("horizon_months", 6),
            drivers_text=drivers_text or "No drivers identified",
            signals_text=signals_text or "No signals available",
            evidence_text=evidence_text or "No evidence items",
            scenario_description=scenario_description,
        )
    
    def _fallback_scenario(
        self,
        evidence_pack: EvidencePack,
        scenario_description: str
    ) -> Dict[str, Any]:
        """Generate fallback when LLM fails"""
        pack = evidence_pack.to_dict() if hasattr(evidence_pack, 'to_dict') else evidence_pack
        
        return {
            "scenario_name": "Scenario Analysis",
            "scenario_description": scenario_description,
            "current_state": {
                "relevant_signals": [],
                "current_risk_score": pack.get("risk_score", 0.0),
                "current_risk_band": pack.get("risk_band", "medium")
            },
            "projected_state": {
                "changed_signals": [],
                "estimated_risk_change": "no_change",
                "confidence": "low"
            },
            "impact_assessment": {
                "overall_impact": "neutral",
                "benefits": ["Unable to generate detailed analysis"],
                "risks": ["Analysis unavailable - review manually"],
                "trade_offs": [],
                "time_to_impact": "Unknown"
            },
            "implementation_path": {
                "steps": [
                    {"step": "Consult with business advisor", "effort": "low", "timeline": "1 week"}
                ],
                "resources_needed": ["Professional consultation"],
                "success_indicators": ["Completed analysis"]
            },
            "alternative_scenarios": [],
            "caveats": [
                "Detailed scenario analysis could not be generated",
                "This is a qualitative estimation only",
            ],
            "agent_version": self.VERSION,
            "generated_at": datetime.now().isoformat(),
            "is_fallback": True,
        }
    
    def _fix_common_issues(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Fix common schema issues"""
        # Ensure required sections
        if "scenario_name" not in result:
            result["scenario_name"] = "Scenario Analysis"
        
        if "current_state" not in result:
            result["current_state"] = {"relevant_signals": []}
        
        if "projected_state" not in result:
            result["projected_state"] = {
                "changed_signals": [],
                "estimated_risk_change": "no_change",
                "confidence": "low"
            }
        
        if "impact_assessment" not in result:
            result["impact_assessment"] = {
                "overall_impact": "neutral",
                "benefits": [],
                "risks": [],
                "trade_offs": [],
                "time_to_impact": "Unknown"
            }
        
        if "implementation_path" not in result:
            result["implementation_path"] = {
                "steps": [],
                "resources_needed": [],
                "success_indicators": []
            }
        
        # Validate enums
        valid_risk_changes = ["significant_decrease", "moderate_decrease", "slight_decrease", 
                             "no_change", "slight_increase", "moderate_increase", "significant_increase"]
        if result.get("projected_state", {}).get("estimated_risk_change") not in valid_risk_changes:
            result["projected_state"]["estimated_risk_change"] = "no_change"
        
        valid_impacts = ["very_positive", "positive", "neutral", "negative", "very_negative"]
        if result.get("impact_assessment", {}).get("overall_impact") not in valid_impacts:
            result["impact_assessment"]["overall_impact"] = "neutral"
        
        return result
    
    def get_version(self) -> str:
        """Return agent version"""
        return self.VERSION
