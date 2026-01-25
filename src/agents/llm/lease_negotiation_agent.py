"""
Lease Negotiation Agent (Nemotron)

Uses risk drivers to propose lease negotiation tactics and scripts.
Output includes: asks, concessions, fallback plan.

Specialized agent for commercial lease negotiations based on business risk profile.
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


LEASE_NEGOTIATION_SCHEMA = {
    "type": "object",
    "required": ["situation_assessment", "primary_asks", "concessions", "fallback_plan", "talking_points"],
    "properties": {
        "situation_assessment": {
            "type": "object",
            "properties": {
                "landlord_leverage": {
                    "type": "string",
                    "enum": ["low", "medium", "high"]
                },
                "tenant_leverage": {
                    "type": "string",
                    "enum": ["low", "medium", "high"]
                },
                "market_conditions": {"type": "string"},
                "key_factors": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "evidence_refs": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        },
        "primary_asks": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["ask", "rationale", "priority"],
                "properties": {
                    "ask": {"type": "string"},
                    "rationale": {"type": "string"},
                    "priority": {
                        "type": "string",
                        "enum": ["must_have", "important", "nice_to_have"]
                    },
                    "suggested_approach": {"type": "string"},
                    "evidence_refs": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        },
        "concessions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["concession", "value_to_landlord"],
                "properties": {
                    "concession": {"type": "string"},
                    "value_to_landlord": {"type": "string"},
                    "your_cost": {"type": "string"},
                    "when_to_offer": {"type": "string"}
                }
            }
        },
        "fallback_plan": {
            "type": "object",
            "required": ["walk_away_point", "alternatives"],
            "properties": {
                "walk_away_point": {"type": "string"},
                "alternatives": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "timeline": {"type": "string"}
            }
        },
        "talking_points": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["scenario", "script"],
                "properties": {
                    "scenario": {"type": "string"},
                    "script": {"type": "string"},
                    "evidence_refs": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        },
        "red_flags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Warning signs during negotiation"
        },
        "disclaimers": {
            "type": "array",
            "items": {"type": "string"}
        }
    }
}

LEASE_NEGOTIATION_PROMPT = """You are an expert commercial lease negotiation advisor for small businesses in San Francisco.

Based on the business risk profile and market signals below, create a comprehensive lease negotiation strategy.

## Business Context
{entity_summary}

## Risk Profile
Risk Score: {risk_score:.2f} ({risk_band})
Horizon: {horizon_months} months

## Risk Drivers (Use these to inform negotiation)
{drivers_text}

## Market Signals
{signals_text}

## Evidence Items
{evidence_text}

## Data Gaps
{data_gaps_text}

## Instructions
Create a lease negotiation strategy with:

1. "situation_assessment": Evaluate leverage for both parties
   - landlord_leverage: "low"/"medium"/"high"
   - tenant_leverage: "low"/"medium"/"high"
   - market_conditions: Current market context
   - key_factors: What drives leverage
   - evidence_refs: Supporting evidence IDs

2. "primary_asks": Your negotiation asks (3-5 items)
   - ask: What you're asking for
   - rationale: Why landlord should agree
   - priority: "must_have"/"important"/"nice_to_have"
   - suggested_approach: How to present it
   - evidence_refs: Evidence supporting this ask

3. "concessions": What you can offer (2-3 items)
   - concession: What you'll offer
   - value_to_landlord: Why they'd want it
   - your_cost: Impact on you
   - when_to_offer: Timing/conditions

4. "fallback_plan": If negotiation fails
   - walk_away_point: Your bottom line
   - alternatives: Other options
   - timeline: How long you can wait

5. "talking_points": Ready-to-use scripts (3-4 scenarios)
   - scenario: The situation
   - script: What to say (actual words)
   - evidence_refs: Data backing the script

6. "red_flags": Warning signs during negotiation

7. "disclaimers": Legal/professional caveats

## CRITICAL RULES
- Reference evidence IDs in all asks and talking points
- Use specific SF market context
- Be realistic about leverage based on risk profile
- Higher risk = more need for protective terms
- Include vacancy/market signals in arguments
- Never provide legal advice

Output ONLY valid JSON."""


class LeaseNegotiationAgent:
    """
    Agent for generating lease negotiation strategies using Nemotron.
    
    Creates comprehensive negotiation plans including:
    - Situation assessment with leverage analysis
    - Prioritized asks with evidence support
    - Strategic concessions
    - Fallback plans and alternatives
    - Ready-to-use talking point scripts
    
    Example:
        agent = LeaseNegotiationAgent()
        strategy = agent.generate(evidence_pack, lease_context={...})
    """
    
    VERSION = "1.0.0"
    TEMPERATURE = 0.3
    MAX_TOKENS = 3500
    
    DISCLAIMERS = [
        "This is not legal advice. Consult a real estate attorney before signing any lease.",
        "Market conditions may have changed since data was collected.",
        "Actual negotiation outcomes depend on many factors not captured here.",
    ]
    
    def __init__(self, nim_client: NIMClient = None):
        self.nim_client = nim_client or NIMClient(timeout=60.0)  # Increased timeout for DGX
        self.validator = SchemaValidator()
    
    def generate(
        self,
        evidence_pack: EvidencePack,
        lease_context: Dict[str, Any] = None,
        temperature: float = None,
    ) -> Dict[str, Any]:
        """
        Generate lease negotiation strategy.
        
        Args:
            evidence_pack: Packaged evidence from EvidencePackagerAgent
            lease_context: Optional context about current lease situation
            temperature: Override default temperature
            
        Returns:
            Structured negotiation strategy
        """
        # Build prompt
        prompt = self._build_prompt(evidence_pack, lease_context)
        
        # Call Nemotron
        response = self.nim_client.chat_structured(
            prompt=prompt,
            output_schema=LEASE_NEGOTIATION_SCHEMA,
            temperature=temperature or self.TEMPERATURE,
            max_tokens=self.MAX_TOKENS,
        )
        
        if not response:
            logger.error("Failed to get response from Nemotron")
            return self._fallback_strategy()
        
        # Parse response
        result = response.parse_json()
        if not result:
            logger.warning("Failed to parse JSON, using fallback")
            return self._fallback_strategy()
        
        # Validate
        is_valid, errors = self.validator.validate(result, LEASE_NEGOTIATION_SCHEMA)
        if not is_valid:
            logger.warning(f"Schema validation failed: {errors}")
            result = self._fix_common_issues(result)
        
        # Always add standard disclaimers
        result["disclaimers"] = self.DISCLAIMERS + result.get("disclaimers", [])
        
        # Add metadata
        result["agent_version"] = self.VERSION
        result["generated_at"] = datetime.now().isoformat()
        
        return result
    
    def _build_prompt(
        self,
        evidence_pack: EvidencePack,
        lease_context: Dict[str, Any] = None
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
        
        # Format signals with focus on lease-relevant data
        signals_text = ""
        lease_relevant = ["vacancy", "evictions", "permits", "dbi_complaints"]
        for cat, summary in pack.get("signal_summaries", {}).items():
            marker = "★ " if cat in lease_relevant else ""
            signals_text += f"- {marker}{cat}: {summary}\n"
        
        # Format evidence
        evidence_text = ""
        for item in pack.get("evidence_items", []):
            eid = item.get("id", "")
            content = item.get("content", "")
            evidence_text += f"- {eid}: {content}\n"
        
        # Format data gaps
        data_gaps_text = "\n".join(f"- {g}" for g in pack.get("data_gaps", [])) or "None"
        
        prompt = LEASE_NEGOTIATION_PROMPT.format(
            entity_summary=pack.get("entity_summary", "Unknown business"),
            risk_score=pack.get("risk_score", 0.0),
            risk_band=pack.get("risk_band", "medium"),
            horizon_months=pack.get("horizon_months", 6),
            drivers_text=drivers_text or "No drivers identified",
            signals_text=signals_text or "No signals available",
            evidence_text=evidence_text or "No evidence items",
            data_gaps_text=data_gaps_text,
        )
        
        # Add lease context if provided
        if lease_context:
            prompt += "\n\n## Current Lease Situation\n"
            for key, value in lease_context.items():
                prompt += f"- {key}: {value}\n"
        
        return prompt
    
    def _fallback_strategy(self) -> Dict[str, Any]:
        """Generate fallback when LLM fails"""
        return {
            "situation_assessment": {
                "landlord_leverage": "medium",
                "tenant_leverage": "medium",
                "market_conditions": "Unable to assess - consult local market data",
                "key_factors": ["Market vacancy rates", "Your payment history", "Location desirability"],
                "evidence_refs": []
            },
            "primary_asks": [
                {
                    "ask": "Rent freeze or reduced increases",
                    "rationale": "Stabilizes costs during uncertain period",
                    "priority": "important",
                    "suggested_approach": "Reference market conditions and your track record",
                    "evidence_refs": []
                }
            ],
            "concessions": [
                {
                    "concession": "Longer lease term",
                    "value_to_landlord": "Guaranteed occupancy",
                    "your_cost": "Reduced flexibility",
                    "when_to_offer": "When asking for rent concessions"
                }
            ],
            "fallback_plan": {
                "walk_away_point": "Terms that threaten business viability",
                "alternatives": ["Explore other locations", "Consider subleasing", "Negotiate month-to-month"],
                "timeline": "60-90 days before lease expires"
            },
            "talking_points": [
                {
                    "scenario": "Initial negotiation meeting",
                    "script": "I value our landlord-tenant relationship and want to find terms that work for both of us...",
                    "evidence_refs": []
                }
            ],
            "red_flags": [
                "Landlord won't negotiate on any terms",
                "Sudden large increases without justification"
            ],
            "disclaimers": self.DISCLAIMERS,
            "agent_version": self.VERSION,
            "generated_at": datetime.now().isoformat(),
            "is_fallback": True,
        }
    
    def _fix_common_issues(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Fix common schema issues"""
        # Ensure required sections exist
        if "situation_assessment" not in result:
            result["situation_assessment"] = {
                "landlord_leverage": "medium",
                "tenant_leverage": "medium",
                "market_conditions": "Not assessed",
                "key_factors": [],
                "evidence_refs": []
            }
        
        if "primary_asks" not in result:
            result["primary_asks"] = []
        
        if "concessions" not in result:
            result["concessions"] = []
        
        if "fallback_plan" not in result:
            result["fallback_plan"] = {
                "walk_away_point": "To be determined",
                "alternatives": [],
                "timeline": "TBD"
            }
        
        if "talking_points" not in result:
            result["talking_points"] = []
        
        # Ensure evidence_refs in asks
        for ask in result.get("primary_asks", []):
            if "evidence_refs" not in ask:
                ask["evidence_refs"] = []
            if ask.get("priority") not in ["must_have", "important", "nice_to_have"]:
                ask["priority"] = "important"
        
        return result
    
    def get_version(self) -> str:
        """Return agent version"""
        return self.VERSION
