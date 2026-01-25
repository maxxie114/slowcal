"""
City Fees Compliance Agent (Nemotron)

Produces compliance checklist, renewal schedules, and possible waiver categories
for San Francisco city fees and business requirements.

IMPORTANT: This is NOT legal advice. Always recommend consulting with
appropriate professionals.
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


COMPLIANCE_SCHEMA = {
    "type": "object",
    "required": ["business_context", "compliance_checklist", "renewal_schedule", "potential_waivers", "disclaimers"],
    "properties": {
        "business_context": {
            "type": "object",
            "properties": {
                "business_type": {"type": "string"},
                "likely_requirements": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "evidence_refs": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        },
        "compliance_checklist": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["item", "category", "status_unknown"],
                "properties": {
                    "item": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["business_registration", "permits", "taxes", "health_safety", "zoning", "other"]
                    },
                    "description": {"type": "string"},
                    "typical_fee": {"type": "string"},
                    "renewal_frequency": {"type": "string"},
                    "agency": {"type": "string"},
                    "website": {"type": "string"},
                    "status_unknown": {"type": "boolean"},
                    "evidence_refs": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        },
        "renewal_schedule": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["item", "frequency", "typical_month"],
                "properties": {
                    "item": {"type": "string"},
                    "frequency": {"type": "string"},
                    "typical_month": {"type": "string"},
                    "advance_notice_days": {"type": "integer"},
                    "late_penalty": {"type": "string"}
                }
            }
        },
        "potential_waivers": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["waiver_name", "eligibility_criteria"],
                "properties": {
                    "waiver_name": {"type": "string"},
                    "eligibility_criteria": {"type": "string"},
                    "potential_savings": {"type": "string"},
                    "how_to_apply": {"type": "string"},
                    "likelihood": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "unknown"]
                    }
                }
            }
        },
        "cost_reduction_tips": {
            "type": "array",
            "items": {"type": "string"}
        },
        "compliance_risks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "risk": {"type": "string"},
                    "consequence": {"type": "string"},
                    "mitigation": {"type": "string"},
                    "evidence_refs": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        },
        "disclaimers": {
            "type": "array",
            "items": {"type": "string"}
        }
    }
}

COMPLIANCE_PROMPT = """You are a compliance advisor helping small businesses understand San Francisco city fees and requirements.

## Business Context
{entity_summary}

## Business Risk Profile
Risk Score: {risk_score:.2f} ({risk_band})

## Available Evidence
{signals_text}

{evidence_text}

## Data Gaps
{data_gaps_text}

## Instructions
Create a compliance guide with:

1. "business_context": 
   - business_type: Inferred type
   - likely_requirements: What they probably need
   - evidence_refs: Supporting evidence IDs

2. "compliance_checklist": Array of compliance items
   For each item:
   - item: Name of requirement
   - category: "business_registration"/"permits"/"taxes"/"health_safety"/"zoning"/"other"
   - description: What it covers
   - typical_fee: Approximate cost
   - renewal_frequency: How often
   - agency: Responsible agency
   - website: Where to find info
   - status_unknown: true (we don't know their actual status)
   - evidence_refs: Evidence IDs if relevant

3. "renewal_schedule": Key renewal dates
   - item: What needs renewal
   - frequency: "annual"/"biennial"/etc
   - typical_month: When it's usually due
   - advance_notice_days: How early to start
   - late_penalty: Consequence of missing

4. "potential_waivers": Possible fee reductions
   - waiver_name: Name of program
   - eligibility_criteria: Who qualifies
   - potential_savings: How much
   - how_to_apply: Process
   - likelihood: "low"/"medium"/"high"/"unknown"

5. "cost_reduction_tips": General advice for reducing fees

6. "compliance_risks": Based on signals
   - risk: What could go wrong
   - consequence: What happens
   - mitigation: How to address
   - evidence_refs: Supporting data

7. "disclaimers": Legal caveats (REQUIRED)

## CRITICAL RULES
- Always mark status_unknown: true - we don't know their actual compliance
- Include SF-specific programs (First Year Free, Small Business waiver, etc.)
- Reference evidence for risks
- This is NOT legal/tax advice - must include appropriate disclaimers
- Fees change - note that amounts are approximate
- Include common SF business requirements

Output ONLY valid JSON."""


class CityFeesComplianceAgent:
    """
    Agent for generating city fees and compliance guidance using Nemotron.
    
    Creates compliance guidance including:
    - Compliance checklist for SF businesses
    - Renewal schedules
    - Potential fee waivers and exemptions
    - Compliance risks based on signals
    
    IMPORTANT: Output always includes disclaimers that this is not legal advice.
    
    Example:
        agent = CityFeesComplianceAgent()
        compliance = agent.analyze(evidence_pack)
    """
    
    VERSION = "1.0.0"
    TEMPERATURE = 0.2
    MAX_TOKENS = 3500
    
    STANDARD_DISCLAIMERS = [
        "This information is for educational purposes only and is NOT legal, tax, or professional advice.",
        "Fee amounts are approximate and subject to change. Verify current amounts with the relevant agency.",
        "Consult with a licensed accountant, attorney, or business advisor before making decisions.",
        "Requirements vary by business type, location, and other factors not fully captured here.",
        "The City of San Francisco updates requirements regularly. Check official sources for current information.",
    ]
    
    def __init__(self, nim_client: NIMClient = None):
        self.nim_client = nim_client or NIMClient(timeout=60.0)  # Increased timeout for DGX
        self.validator = SchemaValidator()
    
    def analyze(
        self,
        evidence_pack: EvidencePack,
        business_type: str = None,
        temperature: float = None,
    ) -> Dict[str, Any]:
        """
        Generate compliance guidance.
        
        Args:
            evidence_pack: Packaged evidence from EvidencePackagerAgent
            business_type: Optional explicit business type
            temperature: Override default temperature
            
        Returns:
            Structured compliance guidance
        """
        # Build prompt
        prompt = self._build_prompt(evidence_pack, business_type)
        
        # Call Nemotron
        response = self.nim_client.chat_structured(
            prompt=prompt,
            output_schema=COMPLIANCE_SCHEMA,
            temperature=temperature or self.TEMPERATURE,
            max_tokens=self.MAX_TOKENS,
        )
        
        if not response:
            logger.error("Failed to get response from Nemotron")
            return self._fallback_guidance()
        
        # Parse response
        result = response.parse_json()
        if not result:
            logger.warning("Failed to parse JSON, using fallback")
            return self._fallback_guidance()
        
        # Validate
        is_valid, errors = self.validator.validate(result, COMPLIANCE_SCHEMA)
        if not is_valid:
            logger.warning(f"Schema validation failed: {errors}")
            result = self._fix_common_issues(result)
        
        # Always ensure disclaimers
        result["disclaimers"] = self.STANDARD_DISCLAIMERS + result.get("disclaimers", [])
        
        # Add metadata
        result["agent_version"] = self.VERSION
        result["generated_at"] = datetime.now().isoformat()
        
        return result
    
    def _build_prompt(
        self,
        evidence_pack: EvidencePack,
        business_type: str = None
    ) -> str:
        """Build prompt from evidence pack"""
        pack = evidence_pack.to_dict() if hasattr(evidence_pack, 'to_dict') else evidence_pack
        
        # Entity summary with business type override
        entity_summary = pack.get("entity_summary", "Unknown business")
        if business_type:
            entity_summary += f" (Business type: {business_type})"
        
        # Format signals
        signals_text = "## Signal Summaries\n"
        for cat, summary in pack.get("signal_summaries", {}).items():
            signals_text += f"- {cat}: {summary}\n"
        
        # Format evidence
        evidence_text = "## Evidence Items\n"
        for item in pack.get("evidence_items", []):
            eid = item.get("id", "")
            content = item.get("content", "")
            evidence_text += f"- {eid}: {content}\n"
        
        # Format data gaps
        data_gaps_text = "\n".join(f"- {g}" for g in pack.get("data_gaps", [])) or "None identified"
        
        return COMPLIANCE_PROMPT.format(
            entity_summary=entity_summary,
            risk_score=pack.get("risk_score", 0.0),
            risk_band=pack.get("risk_band", "medium"),
            signals_text=signals_text,
            evidence_text=evidence_text,
            data_gaps_text=data_gaps_text,
        )
    
    def _fallback_guidance(self) -> Dict[str, Any]:
        """Generate fallback when LLM fails"""
        return {
            "business_context": {
                "business_type": "Unknown",
                "likely_requirements": [
                    "Business Registration Certificate",
                    "Seller's Permit (if selling goods)",
                    "Business Tax Certificate",
                ],
                "evidence_refs": []
            },
            "compliance_checklist": [
                {
                    "item": "Business Registration Certificate",
                    "category": "business_registration",
                    "description": "Required for all businesses operating in SF",
                    "typical_fee": "$50-$500 depending on size",
                    "renewal_frequency": "Annual",
                    "agency": "Office of the Treasurer & Tax Collector",
                    "website": "https://sftreasurer.org/",
                    "status_unknown": True,
                    "evidence_refs": []
                },
                {
                    "item": "Business Property Tax",
                    "category": "taxes",
                    "description": "Annual tax on business personal property",
                    "typical_fee": "Varies by assets",
                    "renewal_frequency": "Annual",
                    "agency": "Office of the Treasurer & Tax Collector",
                    "website": "https://sftreasurer.org/",
                    "status_unknown": True,
                    "evidence_refs": []
                }
            ],
            "renewal_schedule": [
                {
                    "item": "Business Registration",
                    "frequency": "Annual",
                    "typical_month": "May 31",
                    "advance_notice_days": 60,
                    "late_penalty": "10% penalty + interest"
                }
            ],
            "potential_waivers": [
                {
                    "waiver_name": "First Year Free Program",
                    "eligibility_criteria": "New businesses in first year of operation",
                    "potential_savings": "Registration fee waived",
                    "how_to_apply": "Apply during registration",
                    "likelihood": "unknown"
                },
                {
                    "waiver_name": "Small Business Exemption",
                    "eligibility_criteria": "Gross receipts under certain threshold",
                    "potential_savings": "Reduced or waived fees",
                    "how_to_apply": "Check with Tax Collector",
                    "likelihood": "unknown"
                }
            ],
            "cost_reduction_tips": [
                "File renewals on time to avoid penalties",
                "Check if you qualify for small business exemptions",
                "Keep records organized for faster processing"
            ],
            "compliance_risks": [],
            "disclaimers": self.STANDARD_DISCLAIMERS,
            "agent_version": self.VERSION,
            "generated_at": datetime.now().isoformat(),
            "is_fallback": True,
        }
    
    def _fix_common_issues(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Fix common schema issues"""
        # Ensure required sections
        if "business_context" not in result:
            result["business_context"] = {
                "business_type": "Unknown",
                "likely_requirements": [],
                "evidence_refs": []
            }
        
        if "compliance_checklist" not in result:
            result["compliance_checklist"] = []
        
        if "renewal_schedule" not in result:
            result["renewal_schedule"] = []
        
        if "potential_waivers" not in result:
            result["potential_waivers"] = []
        
        if "disclaimers" not in result:
            result["disclaimers"] = []
        
        # Ensure status_unknown is set
        for item in result.get("compliance_checklist", []):
            item["status_unknown"] = True
            if item.get("category") not in ["business_registration", "permits", "taxes", "health_safety", "zoning", "other"]:
                item["category"] = "other"
        
        # Ensure waiver likelihood is valid
        for waiver in result.get("potential_waivers", []):
            if waiver.get("likelihood") not in ["low", "medium", "high", "unknown"]:
                waiver["likelihood"] = "unknown"
        
        return result
    
    def get_version(self) -> str:
        """Return agent version"""
        return self.VERSION
