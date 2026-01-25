"""
LLM Agents for Narrative & Strategy Generation

These agents use Nemotron via NIM for:
- Evidence-grounded explanations
- Action planning with evidence refs
- Policy compliance checking
- Quality assurance

All agents output strict JSON and reference evidence IDs.
"""

from .evidence_packager_agent import EvidencePackagerAgent
from .explanation_agent import ExplanationAgent
from .strategy_planner_agent import StrategyPlannerAgent
from .lease_negotiation_agent import LeaseNegotiationAgent
from .city_fees_compliance_agent import CityFeesComplianceAgent
from .scenario_simulator_agent import ScenarioSimulatorAgent
from .policy_guard_agent import PolicyGuardAgent
from .critic_qa_agent import CriticQAAgent

__all__ = [
    "EvidencePackagerAgent",
    "ExplanationAgent",
    "StrategyPlannerAgent",
    "LeaseNegotiationAgent",
    "CityFeesComplianceAgent",
    "ScenarioSimulatorAgent",
    "PolicyGuardAgent",
    "CriticQAAgent",
]
