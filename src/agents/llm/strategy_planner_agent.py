"""
Strategy Planner Agent (Nemotron) — Primary

Produces prioritized action plans across three horizons:
- 2 weeks (immediate)
- 60 days (short-term)
- 6 months (medium-term)

All recommendations MUST reference evidence IDs provided in the EvidencePack.
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


# Output schema for strategy
STRATEGY_SCHEMA = {
    "type": "object",
    "required": ["summary", "actions", "questions_for_user"],
    "properties": {
        "summary": {
            "type": "string",
            "description": "Executive summary of recommended strategy"
        },
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["horizon", "action", "why", "expected_impact", "effort", "evidence_refs"],
                "properties": {
                    "horizon": {
                        "type": "string",
                        "enum": ["2_weeks", "60_days", "6_months"]
                    },
                    "action": {"type": "string"},
                    "why": {"type": "string"},
                    "expected_impact": {
                        "type": "string",
                        "enum": ["low", "medium", "high"]
                    },
                    "effort": {
                        "type": "string",
                        "enum": ["low", "medium", "high"]
                    },
                    "evidence_refs": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "success_metric": {"type": "string"},
                    "dependencies": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        },
        "questions_for_user": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Questions to gather more context from user"
        },
        "priority_rationale": {
            "type": "string",
            "description": "Explanation of prioritization logic"
        },
        "risk_if_no_action": {
            "type": "string",
            "description": "What happens if no action is taken"
        }
    }
}

STRATEGY_PROMPT_TEMPLATE = """You are a strategic advisor for small businesses in San Francisco. Your task is to create a prioritized action plan to reduce business closure risk.

## Business Context
{entity_summary}

## Risk Assessment
Score: {risk_score:.2f} ({risk_band} risk)
Horizon: {horizon_months} months

## Top Risk Drivers
{drivers_text}

## Signal Summaries
{signals_text}

## Evidence Items (MUST reference these in recommendations)
{evidence_text}

## Data Gaps & Limitations
{data_gaps_text}

## Confidence Notes
{confidence_notes_text}

## Instructions
Create a strategic action plan with:

1. "summary": Brief executive summary (2-3 sentences)

2. "actions": Array of recommended actions. For each action include:
   - "horizon": "2_weeks" | "60_days" | "6_months"
   - "action": Specific, actionable recommendation
   - "why": Why this helps address the risk (connect to evidence)
   - "expected_impact": "low" | "medium" | "high"
   - "effort": "low" | "medium" | "high" (time/cost/complexity)
   - "evidence_refs": REQUIRED - array of evidence IDs supporting this action
   - "success_metric": How to measure success
   - "dependencies": Any prerequisites

3. "questions_for_user": Questions to refine the strategy

4. "priority_rationale": Why you ordered actions this way

5. "risk_if_no_action": Consequences of inaction

## CRITICAL RULES
- Every action MUST have evidence_refs with at least one evidence ID (e.g., ["e:complaints_311-001"])
- Do NOT recommend actions without evidence support
- Prioritize high-impact, low-effort actions first
- Be specific and actionable, not generic
- If data is insufficient, say so and ask clarifying questions
- Include at least 2 actions per time horizon (6 total minimum)

IMPORTANT: You must respond with ONLY a valid JSON object. Do not include any text before or after the JSON. Do not explain what you will do. Start your response directly with the opening brace of the JSON object."""


class StrategyPlannerAgent:
    """
    Primary strategy planning agent using Nemotron.
    
    Creates prioritized action plans across three time horizons:
    - 2 weeks: Immediate actions
    - 60 days: Short-term initiatives
    - 6 months: Medium-term strategic moves
    
    All recommendations are evidence-grounded with explicit references.
    
    Example:
        agent = StrategyPlannerAgent()
        strategy = agent.plan(evidence_pack)
    """
    
    VERSION = "1.0.0"
    TEMPERATURE = 0.2  # Low temp for consistent planning
    MAX_TOKENS = 3000
    
    def __init__(self, nim_client: NIMClient = None):
        self.nim_client = nim_client or NIMClient(timeout=300.0)  # 5 min timeout for DGX
        self.validator = SchemaValidator()
    
    def plan(
        self,
        evidence_pack: EvidencePack,
        temperature: float = None,
        focus_areas: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate strategic action plan from evidence.
        
        Args:
            evidence_pack: Packaged evidence from EvidencePackagerAgent
            temperature: Override default temperature
            focus_areas: Optional list of areas to focus on
            
        Returns:
            Structured strategy dict with actions and recommendations
        """
        try:
            # Build prompt
            prompt = self._build_prompt(evidence_pack, focus_areas)
            
            # Call Nemotron
            response = self.nim_client.chat_structured(
                prompt=prompt,
                output_schema=STRATEGY_SCHEMA,
                temperature=temperature or self.TEMPERATURE,
                max_tokens=self.MAX_TOKENS,
            )
            
            if not response:
                logger.error("Failed to get response from Nemotron")
                return self._fallback_strategy(evidence_pack)
            
            # Parse response
            result = response.parse_json()
            if not result:
                logger.warning("Failed to parse JSON, using fallback")
                return self._fallback_strategy(evidence_pack)
            
            # Validate against schema
            is_valid, errors = self.validator.validate(result, STRATEGY_SCHEMA)
            if not is_valid:
                logger.warning(f"Schema validation failed: {errors}")
                result = self._fix_common_issues(result)
            
            # Post-process to ensure evidence coverage
            result = self._ensure_evidence_coverage(result, evidence_pack)
            
            # Add metadata
            result["agent_version"] = self.VERSION
            result["generated_at"] = datetime.now().isoformat()
            
            return result
        except Exception as e:
            logger.error(f"Strategy planning failed: {e}, using fallback")
            return self._fallback_strategy(evidence_pack)
    
    def _build_prompt(
        self,
        evidence_pack: EvidencePack,
        focus_areas: List[str] = None
    ) -> str:
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
        
        # Format confidence notes
        confidence_notes_text = "\n".join(f"- {n}" for n in pack.get("confidence_notes", [])) or "Standard confidence"
        
        prompt = STRATEGY_PROMPT_TEMPLATE.format(
            entity_summary=pack.get("entity_summary", "Unknown business"),
            risk_score=pack.get("risk_score", 0.0),
            risk_band=pack.get("risk_band", "medium"),
            horizon_months=pack.get("horizon_months", 6),
            drivers_text=drivers_text or "No drivers identified",
            signals_text=signals_text or "No signals available",
            evidence_text=evidence_text or "No evidence items",
            data_gaps_text=data_gaps_text,
            confidence_notes_text=confidence_notes_text,
        )
        
        # Add focus areas if provided
        if focus_areas:
            prompt += f"\n\n## Focus Areas (prioritize these)\n"
            for area in focus_areas:
                prompt += f"- {area}\n"
        
        return prompt
    
    def _fallback_strategy(self, evidence_pack: EvidencePack) -> Dict[str, Any]:
        """Generate intelligent fallback strategy using actual evidence data"""
        pack = evidence_pack.to_dict() if hasattr(evidence_pack, 'to_dict') else evidence_pack
        risk_band = pack.get("risk_band", "medium")
        risk_score = pack.get("risk_score", 0.5)
        entity_summary = pack.get("entity_summary", "Your business")
        drivers = pack.get("top_drivers", [])
        signal_summaries = pack.get("signal_summaries", {})
        evidence_items = pack.get("evidence_items", [])
        
        # Build evidence refs list
        evidence_refs = [item.get("id", "") for item in evidence_items if item.get("id")]
        
        # Generate specific actions based on risk drivers and signals
        actions = []
        
        # Analyze what we know and generate targeted recommendations
        permits_summary = signal_summaries.get("permits", "")
        complaints_summary = signal_summaries.get("complaints_311", "")
        dbi_summary = signal_summaries.get("dbi_complaints", "")
        evictions_summary = signal_summaries.get("evictions", "")
        vacancy_summary = signal_summaries.get("vacancy", "")
        incidents_summary = signal_summaries.get("sfpd_incidents", "")
        
        # === 2 WEEKS: Immediate Actions ===
        
        # Permit-related action
        if "0 permits" in permits_summary or not permits_summary:
            actions.append({
                "horizon": "2_weeks",
                "action": "Conduct a permit compliance audit - verify all business licenses, health permits, and fire safety certificates are current",
                "why": "Businesses with no recent permit activity may have lapsed licenses. Proactive verification prevents costly fines and forced closures.",
                "expected_impact": "medium",
                "effort": "low",
                "evidence_refs": [e for e in evidence_refs if "permits" in e] or ["e:permits-001"],
                "success_metric": "All permits verified and documented, any gaps identified",
                "dependencies": []
            })
        else:
            actions.append({
                "horizon": "2_weeks",
                "action": "Review and organize all active permits and their renewal dates",
                "why": "Staying ahead of permit renewals prevents operational disruptions",
                "expected_impact": "low",
                "effort": "low",
                "evidence_refs": [e for e in evidence_refs if "permits" in e] or ["e:permits-001"],
                "success_metric": "Permit calendar created with all renewal dates",
                "dependencies": []
            })
        
        # Complaint-related action
        if "0 complaints" in complaints_summary or "0 DBI" in dbi_summary:
            actions.append({
                "horizon": "2_weeks",
                "action": "Document your current compliance status and create a 'clean record' baseline",
                "why": "With no recent complaints, now is the ideal time to document your good standing for future reference (lease negotiations, insurance, etc.)",
                "expected_impact": "low",
                "effort": "low",
                "evidence_refs": [e for e in evidence_refs if "complaint" in e.lower()] or ["e:complaints_311-001"],
                "success_metric": "Compliance documentation folder created and organized",
                "dependencies": []
            })
        else:
            actions.append({
                "horizon": "2_weeks",
                "action": "Review and address any open complaints or DBI violations immediately",
                "why": "Unresolved complaints can escalate to fines, liens, or business license revocation",
                "expected_impact": "high",
                "effort": "medium",
                "evidence_refs": [e for e in evidence_refs if "complaint" in e.lower() or "dbi" in e.lower()],
                "success_metric": "All open complaints documented with resolution timeline",
                "dependencies": []
            })
        
        # === 60 DAYS: Short-term Strategic Actions ===
        
        # Lease/location stability action
        eviction_rate = "0.0%" in evictions_summary or "0%" in evictions_summary
        vacancy_rate = "0.0%" in vacancy_summary or "0%" in vacancy_summary
        
        if eviction_rate and vacancy_rate:
            actions.append({
                "horizon": "60_days",
                "action": "Negotiate lease terms with your landlord - your neighborhood has low eviction and vacancy rates, giving you leverage",
                "why": f"Stable neighborhood conditions ({evictions_summary.split(',')[0] if evictions_summary else 'low evictions'}) indicate landlord has incentive to keep good tenants. This is the time to lock in favorable long-term terms.",
                "expected_impact": "high",
                "effort": "medium",
                "evidence_refs": [e for e in evidence_refs if "eviction" in e.lower() or "vacancy" in e.lower()] or ["e:evictions-001", "e:vacancy-001"],
                "success_metric": "Lease renewal or extension signed with improved terms",
                "dependencies": ["Complete compliance audit first"]
            })
        else:
            actions.append({
                "horizon": "60_days",
                "action": "Review your lease terms and consult with a commercial lease attorney",
                "why": "Understanding your rights and obligations is crucial in changing market conditions",
                "expected_impact": "medium",
                "effort": "medium",
                "evidence_refs": [e for e in evidence_refs if "eviction" in e.lower() or "vacancy" in e.lower()],
                "success_metric": "Lease review completed, key dates and obligations documented",
                "dependencies": []
            })
        
        # Financial resilience action
        actions.append({
            "horizon": "60_days",
            "action": "Build a 3-month emergency operating fund and establish a line of credit with your bank",
            "why": f"With a {risk_band} risk profile (score: {risk_score:.2f}), financial reserves provide a buffer against unexpected disruptions like supply chain issues, seasonal slowdowns, or emergency repairs.",
            "expected_impact": "high",
            "effort": "medium",
            "evidence_refs": evidence_refs[:2] if evidence_refs else [],
            "success_metric": "Emergency fund target set and savings plan in place; credit line approved",
            "dependencies": []
        })
        
        # Neighborhood engagement action
        actions.append({
            "horizon": "60_days",
            "action": "Join your local merchant association and attend neighborhood business meetings",
            "why": "Collective advocacy is powerful in San Francisco. Merchant groups often get advance notice of policy changes, construction projects, and can negotiate group rates for services.",
            "expected_impact": "medium",
            "effort": "low",
            "evidence_refs": [],
            "success_metric": "Membership active, attended at least one meeting",
            "dependencies": []
        })
        
        # === 6 MONTHS: Long-term Strategic Initiatives ===
        
        # Diversification action
        actions.append({
            "horizon": "6_months",
            "action": "Develop a secondary revenue stream or expand service offerings",
            "why": "Businesses with multiple revenue sources are more resilient to market changes. Consider online sales, delivery partnerships, or complementary services.",
            "expected_impact": "high",
            "effort": "high",
            "evidence_refs": [],
            "success_metric": "New revenue stream launched and generating at least 10% of total revenue",
            "dependencies": ["Financial reserves in place"]
        })
        
        # Digital presence action
        actions.append({
            "horizon": "6_months",
            "action": "Strengthen your digital presence - update Google Business profile, collect customer reviews, and establish social media presence",
            "why": "Strong online presence builds customer loyalty, attracts new customers, and provides a communication channel during disruptions.",
            "expected_impact": "medium",
            "effort": "medium",
            "evidence_refs": [],
            "success_metric": "Google Business verified and optimized, 20+ customer reviews, active social media",
            "dependencies": []
        })
        
        # Risk monitoring action
        actions.append({
            "horizon": "6_months",
            "action": "Set up a quarterly risk monitoring routine using this platform to track neighborhood changes",
            "why": "Proactive monitoring catches problems early. Track permit activity, complaints, evictions in your area to spot trends before they impact you.",
            "expected_impact": "medium",
            "effort": "low",
            "evidence_refs": evidence_refs,
            "success_metric": "Quarterly risk check calendar set, first review completed",
            "dependencies": []
        })
        
        # Build summary based on risk level
        if risk_band == "low":
            summary = f"{entity_summary} has a low risk profile (score: {risk_score:.2f}). This is a great foundation to build on. Focus on maintaining compliance, strengthening your financial position, and locking in favorable lease terms while conditions are good. The recommended workflow prioritizes preserving your stable position while building resilience for future challenges."
        elif risk_band == "high":
            summary = f"{entity_summary} shows elevated risk (score: {risk_score:.2f}). Immediate action is needed to address compliance issues and stabilize operations. The recommended workflow front-loads critical compliance tasks, then builds toward financial resilience and long-term stability. Prioritize the 2-week actions immediately."
        else:
            summary = f"{entity_summary} has a moderate risk profile (score: {risk_score:.2f}). There's room for improvement, but no immediate crisis. The recommended workflow balances quick compliance wins with strategic initiatives to strengthen your position over the next 6 months."
        
        # Generate priority rationale
        priority_rationale = "Actions are prioritized using the 'quick wins first' framework: (1) Low-effort compliance items prevent fines and establish baseline, (2) Medium-term actions build financial and operational resilience, (3) Long-term initiatives create sustainable competitive advantages. High-impact items are weighted higher within each time horizon."
        
        # Generate risk if no action
        if risk_band == "low":
            risk_if_no_action = "While current risk is low, failure to maintain compliance or prepare for market changes could leave you vulnerable. Neighborhoods can shift quickly in San Francisco - businesses that don't adapt often find themselves behind."
        elif risk_band == "high":
            risk_if_no_action = "Without addressing the identified risk factors, there is significant probability of operational disruption within the next 6 months. This could include fines, forced closures, or lease non-renewal. Immediate action is strongly recommended."
        else:
            risk_if_no_action = "Continued exposure to identified risk factors may lead to gradual erosion of business stability. While no immediate crisis is likely, accumulating small issues can compound into larger problems over time."
        
        return {
            "summary": summary,
            "actions": actions,
            "questions_for_user": [
                "When does your current lease expire, and have you started renewal discussions?",
                "Do you have any pending permit applications or renewals coming up?",
                "What percentage of your revenue comes from your primary product/service vs. secondary offerings?",
                "Are you a member of any local merchant associations or business groups?",
                "What is your current emergency fund situation - how many months of operating expenses do you have saved?",
            ],
            "priority_rationale": priority_rationale,
            "risk_if_no_action": risk_if_no_action,
            "agent_version": self.VERSION,
            "generated_at": datetime.now().isoformat(),
            "is_fallback": True,
            "workflow_plan": {
                "week_1_2": "Compliance audit and documentation",
                "month_1_2": "Lease negotiation and financial planning",
                "month_3_6": "Growth initiatives and monitoring system",
            }
        }
    
    def _fix_common_issues(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Fix common schema validation issues"""
        # Ensure required fields
        if "summary" not in result:
            result["summary"] = "Strategy plan generated - review actions below"
        
        if "actions" not in result or not isinstance(result["actions"], list):
            result["actions"] = []
        
        if "questions_for_user" not in result:
            result["questions_for_user"] = []
        
        # Fix action items
        for action in result.get("actions", []):
            # Ensure horizon is valid
            if action.get("horizon") not in ["2_weeks", "60_days", "6_months"]:
                action["horizon"] = "60_days"
            
            # Ensure impact/effort are valid
            for field in ["expected_impact", "effort"]:
                if action.get(field) not in ["low", "medium", "high"]:
                    action[field] = "medium"
            
            # Ensure evidence_refs exists
            if "evidence_refs" not in action:
                action["evidence_refs"] = []
        
        return result
    
    def _ensure_evidence_coverage(
        self,
        result: Dict[str, Any],
        evidence_pack: EvidencePack
    ) -> Dict[str, Any]:
        """Ensure actions have evidence coverage where possible"""
        pack = evidence_pack.to_dict() if hasattr(evidence_pack, 'to_dict') else evidence_pack
        
        # Get all available evidence IDs
        available_evidence = {
            item.get("id") for item in pack.get("evidence_items", [])
        }
        
        # Track coverage
        actions_without_evidence = []
        
        for i, action in enumerate(result.get("actions", [])):
            if not action.get("evidence_refs"):
                actions_without_evidence.append(i)
        
        # Flag if many actions lack evidence
        if len(actions_without_evidence) > len(result.get("actions", [])) / 2:
            if "limitations" not in result:
                result["limitations"] = []
            result["limitations"].append(
                f"{len(actions_without_evidence)} actions lack direct evidence support - consider with caution"
            )
        
        return result
    
    def get_version(self) -> str:
        """Return agent version"""
        return self.VERSION
