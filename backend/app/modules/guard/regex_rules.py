"""Regex-based heuristic filter for detecting obvious prompt injection attempts."""

import re
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class RegexResult:
    """Result of regex pattern matching."""

    flag: bool
    matched_patterns: List[str]
    score: float  # 0.0 to 1.0


class RegexFilter:
    """Fast first-pass filter using regex patterns to catch obvious attacks."""

    # High-severity patterns: instruction override attempts
    INSTRUCTION_OVERRIDE_PATTERNS = [
        r"\bignore\s+(all|previous|prior|above)\s+instructions\b",
        r"\bforget\s+(all|previous|prior|above)\s+(.*?)\b",
        r"\bdisregard\s+(all|previous|prior)\s+instructions\b",
        r"\boverride\s+system\s+prompt\b",
        r"\bbypass\s+(all\s+)?restrictions\b",
        r"\bdisable\s+(safety|content|filter)",
    ]

    # High-severity patterns: role hijacking
    ROLE_HIJACKING_PATTERNS = [
        r"\byou\s+are\s+(chatgpt|gpt-4|claude|llama|gemini|an\s+ai|a\s+jailbreak)",
        r"\bpretend\s+(you\s+are|to\s+be)\s+",
        r"\bact\s+as\s+",
        r"\byou\s+will\s+(act|roleplay|behave)\s+as\b",
        r"\bassume\s+(the\s+)?role\s+of\b",
    ]

    # Medium-severity patterns: system prompt disclosure
    PROMPT_DISCLOSURE_PATTERNS = [
        r"\b(system|initial)\s+prompt\b",
        r"\bwhat\s+(are|is|was)\s+your\s+(system\s+)?prompt",
        r"\bshow\s+(me\s+)?(the\s+)?(system\s+)?prompt",
        r"\breveal\s+.*?prompt\b",
        r"\breturn\s+the\s+(original\s+)?system\s+prompt\b",
    ]

    # Medium-severity patterns: policy bypass
    POLICY_BYPASS_PATTERNS = [
        r"\bjailbreak\b",
        r"\bdeveloper\s+mode\b",
        r"\bgod\s+mode\b",
        r"\bunrestricted\s+mode\b",
        r"\bremove\s+all\s+restrictions\b",
        r"\bmemories?\s+(disabled|removed|cleared)\b",
    ]

    # Medium-severity patterns: dangerous code patterns
    DANGEROUS_CODE_PATTERNS = [
        r"\b(rm|del)\s+-rf\s+/\b",  # Destructive shell commands
        r"DROP\s+TABLE\b",  # SQL injection
        r"DELETE\s+FROM\b",  # SQL deletion
        r"UNION\s+SELECT\b",  # SQL injection technique
        r"exec\s*\(",  # Code execution
        r"eval\s*\(",  # Code evaluation
    ]

    # Low-severity patterns: suspicious keywords (context-dependent)
    SUSPICIOUS_KEYWORDS = [
        r"\b(payload|shellcode|exploit|vulnerability)\b",
        r"\b(private|secret|confidential|classified)\b",
        r"\b(backdoor|trojan|malware)\b",
    ]

    def __init__(self):
        """Initialize compiled regex patterns with flags."""
        self.patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Compile all regex patterns with appropriate flags."""
        patterns = {
            "high_override": [
                re.compile(p, re.IGNORECASE) for p in self.INSTRUCTION_OVERRIDE_PATTERNS
            ],
            "high_role": [
                re.compile(p, re.IGNORECASE) for p in self.ROLE_HIJACKING_PATTERNS
            ],
            "medium_disclosure": [
                re.compile(p, re.IGNORECASE) for p in self.PROMPT_DISCLOSURE_PATTERNS
            ],
            "medium_bypass": [
                re.compile(p, re.IGNORECASE) for p in self.POLICY_BYPASS_PATTERNS
            ],
            "medium_code": [
                re.compile(p, re.IGNORECASE) for p in self.DANGEROUS_CODE_PATTERNS
            ],
            "low_keywords": [
                re.compile(p, re.IGNORECASE) for p in self.SUSPICIOUS_KEYWORDS
            ],
        }
        return patterns

    def check(self, prompt: str) -> RegexResult:
        """
        Check prompt against regex patterns.

        Args:
            prompt: User input prompt to check

        Returns:
            RegexResult with flag, matched patterns, and risk score
        """
        matched_patterns = []
        severity_scores = []

        # Check high-severity patterns (instruction override)
        for pattern in self.patterns["high_override"]:
            if pattern.search(prompt):
                match = pattern.search(prompt).group(0)
                matched_patterns.append(f"instruction_override: {match}")
                severity_scores.append(1.0)

        # Check high-severity patterns (role hijacking)
        for pattern in self.patterns["high_role"]:
            if pattern.search(prompt):
                match = pattern.search(prompt).group(0)
                matched_patterns.append(f"role_hijacking: {match}")
                severity_scores.append(1.0)

        # Check medium-severity patterns (prompt disclosure)
        for pattern in self.patterns["medium_disclosure"]:
            if pattern.search(prompt):
                match = pattern.search(prompt).group(0)
                matched_patterns.append(f"prompt_disclosure: {match}")
                severity_scores.append(0.7)

        # Check medium-severity patterns (policy bypass)
        for pattern in self.patterns["medium_bypass"]:
            if pattern.search(prompt):
                match = pattern.search(prompt).group(0)
                matched_patterns.append(f"policy_bypass: {match}")
                severity_scores.append(0.7)

        # Check medium-severity patterns (dangerous code)
        for pattern in self.patterns["medium_code"]:
            if pattern.search(prompt):
                match = pattern.search(prompt).group(0)
                matched_patterns.append(f"dangerous_code: {match}")
                severity_scores.append(0.8)

        # Check low-severity patterns
        for pattern in self.patterns["low_keywords"]:
            if pattern.search(prompt):
                match = pattern.search(prompt).group(0)
                matched_patterns.append(f"suspicious_keyword: {match}")
                severity_scores.append(0.3)

        # Calculate overall risk score (max of all severities)
        risk_score = max(severity_scores) if severity_scores else 0.0

        return RegexResult(
            flag=len(matched_patterns) > 0,
            matched_patterns=matched_patterns,
            score=risk_score,
        )
