"""
Policy Guard Agent

Checks outputs for unsafe or non-compliant guidance.
Enforces "not legal advice" disclaimers and flags sensitive data usage.

This is a validation/safety layer that reviews other agents' outputs.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Patterns to flag
SENSITIVE_PATTERNS = [
    # Legal advice indicators
    (r'\b(you should sue|file a lawsuit|legal action)\b', 'legal_advice', 'high'),
    (r'\b(breach of contract|liable for|damages claim)\b', 'legal_advice', 'medium'),
    
    # Medical advice
    (r'\b(diagnos|treatment|prescription|medical advice)\b', 'medical_advice', 'high'),
    
    # Financial advice without disclaimer
    (r'\b(guaranteed return|investment advice|financial planning)\b', 'financial_advice', 'medium'),
    
    # Discriminatory language
    (r'\b(discriminat|racial|ethnic group|gender-based)\b', 'discrimination', 'high'),
    
    # PII patterns
    (r'\b\d{3}-\d{2}-\d{4}\b', 'ssn_pattern', 'critical'),  # SSN
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'email_pattern', 'low'),  # Email
    
    # Absolute claims
    (r'\b(guaranteed|100% certain|definitely will|always works)\b', 'absolute_claim', 'medium'),
]

# Required disclaimers by content type
REQUIRED_DISCLAIMERS = {
    'legal': [
        "not legal advice",
        "consult.*attorney",
        "consult.*lawyer",
    ],
    'financial': [
        "not financial advice",
        "consult.*accountant",
        "consult.*financial advisor",
    ],
    'compliance': [
        "not legal advice",
        "not tax advice",
        "verify.*official",
    ],
}


class PolicyGuardAgent:
    """
    Agent that validates outputs for policy compliance.
    
    Checks for:
    - Unsafe or non-compliant guidance
    - Missing required disclaimers
    - Sensitive data exposure
    - Inappropriate absolute claims
    
    This is a validation layer, not a content generator.
    
    Example:
        guard = PolicyGuardAgent()
        result = guard.validate(output_dict, content_type="compliance")
        if not result["is_valid"]:
            # Handle violations
            for violation in result["violations"]:
                print(f"Issue: {violation['issue']}")
    """
    
    VERSION = "1.0.0"
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize PolicyGuardAgent.
        
        Args:
            strict_mode: If True, treat medium severity as high
        """
        self.strict_mode = strict_mode
    
    def validate(
        self,
        content: Dict[str, Any],
        content_type: str = "general",
        check_disclaimers: bool = True,
    ) -> Dict[str, Any]:
        """
        Validate content for policy compliance.
        
        Args:
            content: Dictionary containing output to validate
            content_type: Type of content ("legal", "financial", "compliance", "general")
            check_disclaimers: Whether to check for required disclaimers
            
        Returns:
            Validation result with violations and recommendations
        """
        violations = []
        warnings = []
        
        # Convert content to string for pattern matching
        content_str = self._flatten_to_string(content)
        
        # Check for sensitive patterns
        pattern_violations = self._check_patterns(content_str)
        violations.extend([v for v in pattern_violations if v["severity"] in ["critical", "high"]])
        warnings.extend([v for v in pattern_violations if v["severity"] in ["medium", "low"]])
        
        # Check for required disclaimers
        if check_disclaimers:
            disclaimer_issues = self._check_disclaimers(content, content_type)
            if disclaimer_issues:
                violations.append({
                    "issue": "missing_disclaimers",
                    "details": disclaimer_issues,
                    "severity": "high",
                    "recommendation": "Add required disclaimers to output"
                })
        
        # Check for absolute claims without evidence
        absolute_issues = self._check_absolute_claims(content)
        warnings.extend(absolute_issues)
        
        # Check for evidence coverage (if applicable)
        evidence_issues = self._check_evidence_coverage(content)
        if evidence_issues:
            warnings.append({
                "issue": "insufficient_evidence",
                "details": evidence_issues,
                "severity": "medium",
                "recommendation": "Ensure claims reference evidence IDs"
            })
        
        # Determine overall validity
        is_valid = len(violations) == 0
        
        # In strict mode, warnings become violations
        if self.strict_mode:
            high_severity_warnings = [w for w in warnings if w.get("severity") == "medium"]
            if high_severity_warnings:
                is_valid = False
                violations.extend(high_severity_warnings)
        
        return {
            "is_valid": is_valid,
            "violations": violations,
            "warnings": warnings,
            "content_type": content_type,
            "checked_at": datetime.now().isoformat(),
            "agent_version": self.VERSION,
        }
    
    def add_disclaimers(
        self,
        content: Dict[str, Any],
        content_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Add appropriate disclaimers to content.
        
        Args:
            content: Content dictionary
            content_type: Type of content
            
        Returns:
            Content with disclaimers added
        """
        disclaimers = content.get("disclaimers", [])
        
        if content_type in ["legal", "compliance"]:
            disclaimers.extend([
                "This is not legal advice. Consult a licensed attorney for legal matters.",
                "This is not tax advice. Consult a licensed accountant or tax professional.",
            ])
        
        if content_type == "financial":
            disclaimers.extend([
                "This is not financial advice. Consult a licensed financial advisor.",
            ])
        
        # Always add general disclaimer
        disclaimers.append(
            "Information provided is for educational purposes only. Verify with official sources."
        )
        
        # Deduplicate
        content["disclaimers"] = list(dict.fromkeys(disclaimers))
        
        return content
    
    def sanitize(
        self,
        content: Dict[str, Any],
        remove_pii: bool = True,
    ) -> Dict[str, Any]:
        """
        Sanitize content by removing or masking sensitive information.
        
        Args:
            content: Content dictionary
            remove_pii: Whether to remove PII patterns
            
        Returns:
            Sanitized content
        """
        if not remove_pii:
            return content
        
        # Convert to string, sanitize, convert back
        content_str = self._flatten_to_string(content)
        
        # Mask SSN patterns
        content_str = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', 'XXX-XX-XXXX', content_str)
        
        # Note: More sophisticated sanitization would require deep dict traversal
        # This is a simplified version
        
        return content
    
    def _flatten_to_string(self, content: Any, depth: int = 0) -> str:
        """Recursively flatten content to string for pattern matching"""
        if depth > 10:  # Prevent infinite recursion
            return ""
        
        if isinstance(content, str):
            return content
        
        if isinstance(content, dict):
            parts = []
            for key, value in content.items():
                parts.append(f"{key}: {self._flatten_to_string(value, depth + 1)}")
            return " ".join(parts)
        
        if isinstance(content, list):
            return " ".join(self._flatten_to_string(item, depth + 1) for item in content)
        
        return str(content) if content is not None else ""
    
    def _check_patterns(self, content_str: str) -> List[Dict[str, Any]]:
        """Check content against sensitive patterns"""
        violations = []
        content_lower = content_str.lower()
        
        for pattern, issue_type, severity in SENSITIVE_PATTERNS:
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            if matches:
                violations.append({
                    "issue": issue_type,
                    "matches": list(set(matches))[:5],  # Limit matches shown
                    "severity": severity,
                    "recommendation": self._get_recommendation(issue_type)
                })
        
        return violations
    
    def _check_disclaimers(
        self,
        content: Dict[str, Any],
        content_type: str
    ) -> List[str]:
        """Check for required disclaimers"""
        required = REQUIRED_DISCLAIMERS.get(content_type, [])
        if not required:
            return []
        
        # Get existing disclaimers
        disclaimers = content.get("disclaimers", [])
        disclaimers_str = " ".join(str(d).lower() for d in disclaimers)
        
        # Also check limitations
        limitations = content.get("limitations", [])
        limitations_str = " ".join(str(l).lower() for l in limitations)
        
        all_disclaimer_text = disclaimers_str + " " + limitations_str
        
        missing = []
        for req_pattern in required:
            if not re.search(req_pattern, all_disclaimer_text, re.IGNORECASE):
                missing.append(req_pattern)
        
        return missing
    
    def _check_absolute_claims(self, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for absolute claims without evidence"""
        warnings = []
        content_str = self._flatten_to_string(content)
        
        absolute_patterns = [
            r'\bwill definitely\b',
            r'\bguaranteed to\b',
            r'\balways\b',
            r'\bnever\b',
            r'\b100%\b',
            r'\bcertainly will\b',
        ]
        
        for pattern in absolute_patterns:
            if re.search(pattern, content_str, re.IGNORECASE):
                warnings.append({
                    "issue": "absolute_claim",
                    "pattern": pattern,
                    "severity": "low",
                    "recommendation": "Use qualified language (e.g., 'may', 'typically', 'in most cases')"
                })
                break  # Only flag once
        
        return warnings
    
    def _check_evidence_coverage(self, content: Dict[str, Any]) -> List[str]:
        """Check that claims have evidence references"""
        issues = []
        
        # Check strategy actions
        actions = content.get("strategy", {}).get("actions", [])
        if not actions:
            actions = content.get("actions", [])
        
        for i, action in enumerate(actions):
            if not action.get("evidence_refs"):
                issues.append(f"Action {i+1} lacks evidence_refs")
        
        # Check talking points
        talking_points = content.get("talking_points", [])
        for i, point in enumerate(talking_points):
            if not point.get("evidence_refs"):
                issues.append(f"Talking point {i+1} lacks evidence_refs")
        
        return issues[:5]  # Limit issues reported
    
    def _get_recommendation(self, issue_type: str) -> str:
        """Get recommendation for issue type"""
        recommendations = {
            "legal_advice": "Remove or rephrase as information, not advice. Add 'consult an attorney' disclaimer.",
            "medical_advice": "Remove medical claims. This is outside scope of business risk analysis.",
            "financial_advice": "Add 'not financial advice' disclaimer. Qualify statements.",
            "discrimination": "Remove discriminatory language. Focus on objective business factors.",
            "ssn_pattern": "CRITICAL: Remove SSN data immediately. This is PII.",
            "email_pattern": "Consider removing or masking email addresses for privacy.",
            "absolute_claim": "Use qualified language. Add uncertainty where appropriate.",
        }
        return recommendations.get(issue_type, "Review and address this issue")
    
    def get_version(self) -> str:
        """Return agent version"""
        return self.VERSION
