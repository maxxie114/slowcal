"""
Agents module for the SF Business Intelligence Platform

Multi-agent architecture for risk analysis:
- Data Agents: Fetch and aggregate signals from DataSF
- Identity Agents: Resolve entities and normalize addresses
- ML Agents: Feature engineering and risk scoring
- LLM Agents: Narrative generation and strategy planning

Orchestrated by CaseManagerAgent for end-to-end analysis.
"""

from .case_manager import CaseManagerAgent

__all__ = ["CaseManagerAgent"]
