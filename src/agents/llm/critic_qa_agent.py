"""
Critic QA Agent (Nemotron or smaller local model)

Validates outputs from other agents for:
1. Every claim references evidence IDs
2. Recommendations map to drivers
3. Uncertainty is explicit when data gaps exist

Returns either "PASS" or "FAIL + patch plan".

This is the final quality gate before returning results to users.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Import path handling
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.nim_client import NIMClient


class CriticQAAgent:
    """
    Quality assurance agent that validates analysis outputs.
    
    Performs three critical checks:
    1. Evidence Coverage: Every claim must reference evidence IDs
    2. Driver Alignment: Recommendations must address identified drivers
    3. Uncertainty Disclosure: Data gaps must be explicitly stated
    
    Can operate in two modes:
    - Deterministic: Rule-based validation (fast, always available)
    - LLM-assisted: Uses Nemotron for nuanced validation (more thorough)
    
    Example:
        critic = CriticQAAgent()
        result = critic.validate(analysis_output)
        if result["status"] == "FAIL":
            patched = critic.patch(analysis_output, result["patch_plan"])
    """
    
    VERSION = "1.0.0"
    
    # Minimum thresholds (relaxed for fallback scenarios)
    MIN_EVIDENCE_COVERAGE = 0.50  # 50% of claims should have evidence
    MIN_DRIVER_ALIGNMENT = 0.30   # 30% of actions should align with drivers
    
    # Thresholds for strict mode (when LLM provides full analysis)
    STRICT_EVIDENCE_COVERAGE = 0.80
    STRICT_DRIVER_ALIGNMENT = 0.70
    
    def __init__(
        self,
        nim_client: NIMClient = None,
        use_llm: bool = False,
    ):
        """
        Initialize CriticQAAgent.
        
        Args:
            nim_client: NIM client for LLM-assisted validation
            use_llm: Whether to use LLM for validation (default: deterministic)
        """
        self.nim_client = nim_client
        self.use_llm = use_llm and nim_client is not None
    
    def validate(
        self,
        analysis: Dict[str, Any],
        evidence_pack: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Validate analysis output.
        
        Args:
            analysis: Complete analysis output to validate
            evidence_pack: Original evidence pack (for cross-referencing)
            
        Returns:
            Validation result with status, issues, and patch plan
        """
        issues = []
        patch_plan = []
        
        # Detect if using fallback mode (relaxed validation)
        strategy = analysis.get("strategy", {})
        is_fallback = strategy.get("is_fallback", False)
        
        # Adjust thresholds for fallback mode
        if is_fallback:
            self._current_evidence_threshold = self.MIN_EVIDENCE_COVERAGE
            self._current_driver_threshold = self.MIN_DRIVER_ALIGNMENT
        else:
            self._current_evidence_threshold = self.STRICT_EVIDENCE_COVERAGE
            self._current_driver_threshold = self.STRICT_DRIVER_ALIGNMENT
        
        # Check 1: Evidence Coverage
        evidence_result = self._check_evidence_coverage(analysis, evidence_pack)
        if not evidence_result["passed"]:
            issues.append(evidence_result)
            patch_plan.extend(evidence_result.get("patches", []))
        
        # Check 2: Driver Alignment
        driver_result = self._check_driver_alignment(analysis)
        if not driver_result["passed"]:
            issues.append(driver_result)
            patch_plan.extend(driver_result.get("patches", []))
        
        # Check 3: Uncertainty Disclosure
        uncertainty_result = self._check_uncertainty_disclosure(analysis)
        if not uncertainty_result["passed"]:
            issues.append(uncertainty_result)
            patch_plan.extend(uncertainty_result.get("patches", []))
        
        # Check 4: Schema Completeness
        schema_result = self._check_schema_completeness(analysis)
        if not schema_result["passed"]:
            issues.append(schema_result)
            patch_plan.extend(schema_result.get("patches", []))
        
        # Determine overall status
        # In fallback mode, only fail if there are critical issues
        critical_issues = [i for i in issues if i.get("severity") == "critical"]
        
        if is_fallback:
            # Relaxed: Only fail on critical issues
            status = "FAIL" if critical_issues else "PASS"
        else:
            # Strict: Fail on critical or 3+ issues
            status = "FAIL" if critical_issues or len(issues) >= 3 else "PASS"
        
        # If using LLM and failed, get additional insights
        llm_feedback = None
        if status == "FAIL" and self.use_llm and self.nim_client:
            llm_feedback = self._get_llm_feedback(analysis, issues)
        
        return {
            "status": status,
            "issues": issues,
            "issue_count": len(issues),
            "critical_count": len(critical_issues),
            "patch_plan": patch_plan,
            "llm_feedback": llm_feedback,
            "validated_at": datetime.now().isoformat(),
            "agent_version": self.VERSION,
        }
    
    def patch(
        self,
        analysis: Dict[str, Any],
        patch_plan: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Apply patches to fix identified issues.
        
        Args:
            analysis: Original analysis output
            patch_plan: List of patches to apply
            
        Returns:
            Patched analysis output
        """
        patched = analysis.copy()
        
        for patch in patch_plan:
            patch_type = patch.get("type")
            
            if patch_type == "add_limitation":
                if "limitations" not in patched:
                    patched["limitations"] = []
                patched["limitations"].append(patch.get("content"))
            
            elif patch_type == "add_evidence_warning":
                if "audit" not in patched:
                    patched["audit"] = {}
                patched["audit"]["evidence_coverage_warning"] = patch.get("content")
            
            elif patch_type == "flag_action":
                # Flag specific actions as lacking evidence
                action_idx = patch.get("action_index")
                if action_idx is not None:
                    strategy = patched.get("strategy", {})
                    actions = strategy.get("actions", [])
                    if action_idx < len(actions):
                        actions[action_idx]["needs_evidence"] = True
            
            elif patch_type == "add_data_gap":
                if "limitations" not in patched:
                    patched["limitations"] = []
                patched["limitations"].append(f"Data gap: {patch.get('content')}")
        
        # Mark as patched
        if "audit" not in patched:
            patched["audit"] = {}
        patched["audit"]["qa_patched"] = True
        patched["audit"]["patches_applied"] = len(patch_plan)
        
        return patched
    
    def _check_evidence_coverage(
        self,
        analysis: Dict[str, Any],
        evidence_pack: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Check that claims reference evidence IDs"""
        # Count items that should have evidence
        items_checked = 0
        items_with_evidence = 0
        missing_evidence = []
        
        # Check strategy actions
        strategy = analysis.get("strategy", {})
        actions = strategy.get("actions", analysis.get("actions", []))
        
        for i, action in enumerate(actions):
            items_checked += 1
            refs = action.get("evidence_refs", [])
            if refs:
                items_with_evidence += 1
            else:
                missing_evidence.append(f"action_{i}: {action.get('action', '')[:50]}...")
        
        # Check top drivers
        risk = analysis.get("risk", {})
        drivers = risk.get("top_drivers", [])
        
        for i, driver in enumerate(drivers):
            items_checked += 1
            refs = driver.get("evidence_refs", [])
            if refs:
                items_with_evidence += 1
            else:
                missing_evidence.append(f"driver_{i}: {driver.get('driver', '')}")
        
        # Calculate coverage
        coverage = items_with_evidence / max(items_checked, 1)
        threshold = getattr(self, '_current_evidence_threshold', self.MIN_EVIDENCE_COVERAGE)
        passed = coverage >= threshold
        
        patches = []
        if not passed:
            patches.append({
                "type": "add_evidence_warning",
                "content": f"Evidence coverage is {coverage:.0%}, below {threshold:.0%} threshold"
            })
            for item in missing_evidence[:3]:  # Top 3
                patches.append({
                    "type": "add_limitation",
                    "content": f"Recommendation lacks evidence support: {item}"
                })
        
        return {
            "check": "evidence_coverage",
            "passed": passed,
            "score": coverage,
            "threshold": threshold,
            "items_checked": items_checked,
            "items_with_evidence": items_with_evidence,
            "missing_evidence": missing_evidence[:5],
            "severity": "critical" if coverage < 0.3 else "warning",
            "patches": patches,
        }
    
    def _check_driver_alignment(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Check that recommendations align with identified drivers"""
        # Get drivers
        risk = analysis.get("risk", {})
        drivers = risk.get("top_drivers", [])
        driver_names = [d.get("driver", "").lower() for d in drivers]
        
        # Get actions
        strategy = analysis.get("strategy", {})
        actions = strategy.get("actions", analysis.get("actions", []))
        
        aligned_count = 0
        unaligned_actions = []
        
        for i, action in enumerate(actions):
            action_text = f"{action.get('action', '')} {action.get('why', '')}".lower()
            
            # Check if action mentions any driver
            is_aligned = any(driver in action_text for driver in driver_names if driver)
            
            if is_aligned:
                aligned_count += 1
            else:
                unaligned_actions.append(f"action_{i}")
        
        alignment = aligned_count / max(len(actions), 1)
        threshold = getattr(self, '_current_driver_threshold', self.MIN_DRIVER_ALIGNMENT)
        passed = alignment >= threshold or len(drivers) == 0
        
        patches = []
        if not passed:
            patches.append({
                "type": "add_limitation",
                "content": f"Some recommendations may not directly address identified risk drivers"
            })
        
        return {
            "check": "driver_alignment",
            "passed": passed,
            "score": alignment,
            "threshold": threshold,
            "drivers_found": len(drivers),
            "actions_aligned": aligned_count,
            "actions_total": len(actions),
            "unaligned_actions": unaligned_actions[:3],
            "severity": "warning",
            "patches": patches,
        }
    
    def _check_uncertainty_disclosure(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Check that uncertainty is disclosed when data gaps exist"""
        # Look for data gaps
        audit = analysis.get("audit", {})
        limitations = analysis.get("limitations", [])
        
        # Check for data gaps in various places
        data_gaps = []
        
        # From signals
        signals = analysis.get("signals", {})
        for signal_name, signal_data in signals.items():
            if isinstance(signal_data, dict):
                gaps = signal_data.get("data_gaps", [])
                data_gaps.extend(gaps)
                
                freshness = signal_data.get("freshness", {})
                # Handle case where freshness is a string (ISO timestamp) not a dict
                if isinstance(freshness, dict) and freshness.get("is_stale"):
                    data_gaps.append(f"{signal_name} data is stale")
        
        # Check if entity match confidence is low
        entity = analysis.get("entity", {})
        match_confidence = entity.get("match_confidence", 1.0)
        if match_confidence < 0.8:
            data_gaps.append(f"Low entity match confidence ({match_confidence:.0%})")
        
        # Check if limitations mention uncertainty
        has_uncertainty_disclosure = any(
            any(word in lim.lower() for word in ["uncertain", "gap", "missing", "incomplete", "stale"])
            for lim in limitations
        )
        
        # Determine if disclosure is adequate
        needs_disclosure = len(data_gaps) > 0
        has_disclosure = has_uncertainty_disclosure or len(limitations) > 0
        
        passed = not needs_disclosure or has_disclosure
        
        patches = []
        if not passed:
            for gap in data_gaps[:3]:
                patches.append({
                    "type": "add_data_gap",
                    "content": gap
                })
        
        return {
            "check": "uncertainty_disclosure",
            "passed": passed,
            "data_gaps_found": len(data_gaps),
            "has_disclosure": has_disclosure,
            "data_gaps": data_gaps[:5],
            "severity": "warning" if len(data_gaps) <= 2 else "critical",
            "patches": patches,
        }
    
    def _check_schema_completeness(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Check that required fields are present"""
        required_fields = [
            ("case_id", "root"),
            ("entity", "root"),
            ("risk", "root"),
            ("risk.score", "risk"),
            ("risk.band", "risk"),
            ("strategy", "root"),
            ("audit", "root"),
        ]
        
        missing_fields = []
        
        for field_path, parent in required_fields:
            parts = field_path.split(".")
            current = analysis
            
            try:
                for part in parts:
                    current = current[part]
            except (KeyError, TypeError):
                missing_fields.append(field_path)
        
        passed = len(missing_fields) == 0
        
        patches = []
        if not passed:
            patches.append({
                "type": "add_limitation",
                "content": f"Analysis is incomplete: missing {', '.join(missing_fields)}"
            })
        
        return {
            "check": "schema_completeness",
            "passed": passed,
            "missing_fields": missing_fields,
            "severity": "critical" if len(missing_fields) > 2 else "warning",
            "patches": patches,
        }
    
    def _get_llm_feedback(
        self,
        analysis: Dict[str, Any],
        issues: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Get LLM feedback on how to improve"""
        if not self.nim_client:
            return None
        
        prompt = f"""You are a quality assurance reviewer for business risk analysis.

The following analysis has these issues:
{[f"- {i['check']}: {i.get('severity', 'unknown')} - passed: {i['passed']}" for i in issues]}

Provide 2-3 specific suggestions to improve the analysis quality.
Focus on:
1. Adding evidence references where missing
2. Better aligning recommendations with identified risks
3. Being explicit about uncertainty

Keep response under 200 words."""

        try:
            response = self.nim_client.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=300,
            )
            return response.content if response else None
        except Exception as e:
            logger.warning(f"Failed to get LLM feedback: {e}")
            return None
    
    def get_version(self) -> str:
        """Return agent version"""
        return self.VERSION
