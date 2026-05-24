"""Prompt sanitization layer for neutralizing injection risks while preserving UX."""

import re
from typing import Tuple
from enum import Enum


class SanitizationLevel(Enum):
    """Sanitization aggressiveness levels."""
    LOW = "low"  # Preserve intent, minimal risk
    MEDIUM = "medium"  # Balanced approach
    HIGH = "high"  # Aggressive, maximum security


class PromptSanitizer:
    """Neutralizes prompt injection risks by removing meta-instructions and re-wrapping prompts."""

    # Meta-instruction phrases to remove
    META_INSTRUCTIONS = [
        r"ignore\s+(all\s+)?(previous|prior|above|existing)(\s+instructions)?",
        r"forget\s+(everything|all).*?before",
        r"disregard\s+(the\s+)?(system\s+prompt|instructions)",
        r"override\s+(all\s+)?(instructions|prompts|settings)",
        r"you\s+are\s+now\s+in\s+(jailbreak|developer)\s+mode",
        r"act\s+as\s+.*?\s+instead",
        r"pretend\s+(you\s+)?are",
        r"assume\s+the\s+role\s+of",
        r"respond\s+only\s+as",
    ]

    # Role-playing phrases
    ROLE_PHRASES = [
        r"as\s+a\s+\w+,",
        r"in\s+the\s+role\s+of",
        r"acting\s+as",
        r"pretending\s+to\s+be",
        r"you\s+are\s+a\s+\w+",
        r"role:\s*\w+",
    ]

    # Dangerous multi-line separators
    SEPARATORS = [
        r"---+",
        r"===+",
        r"####+",
        r"\|\|\|+",
    ]

    def __init__(self, level: SanitizationLevel = SanitizationLevel.MEDIUM):
        """
        Initialize sanitizer with aggressiveness level.
        
        Args:
            level: Sanitization level (LOW, MEDIUM, HIGH)
        """
        self.level = level
        self.meta_patterns = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in self.META_INSTRUCTIONS]
        self.role_patterns = [re.compile(p, re.IGNORECASE) for p in self.ROLE_PHRASES]
        self.separator_patterns = [re.compile(p) for p in self.SEPARATORS]

    def sanitize(self, prompt: str) -> Tuple[str, str]:
        """
        Sanitize a prompt by removing meta-instructions and dangerous patterns.
        
        Args:
            prompt: Original prompt to sanitize
            
        Returns:
            Tuple of (sanitized_prompt, summary_of_changes)
        """
        original = prompt
        sanitized = prompt

        # Remove meta-instructions
        for pattern in self.meta_patterns:
            matches = pattern.findall(sanitized)
            if matches and self.level != SanitizationLevel.LOW:
                sanitized = pattern.sub("", sanitized)

        # Remove role-playing phrases (aggressive in HIGH mode)
        if self.level == SanitizationLevel.HIGH:
            for pattern in self.role_patterns:
                sanitized = pattern.sub("", sanitized)

        # Normalize multiple spaces
        sanitized = re.sub(r"\s+", " ", sanitized).strip()

        # Handle section separators (medium/high only)
        if self.level in [SanitizationLevel.MEDIUM, SanitizationLevel.HIGH]:
            for pattern in self.separator_patterns:
                if pattern.search(sanitized):
                    # Keep only the first section
                    parts = pattern.split(sanitized)
                    sanitized = parts[0].strip()

        # Truncate if needed
        max_length = 2000
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "..."

        # Generate summary of changes
        changes = []
        if sanitized != original:
            length_reduction = len(original) - len(sanitized)
            changes.append(f"Removed {length_reduction} characters")
            
            if any(pattern.search(original) for pattern in self.meta_patterns):
                changes.append("Removed meta-instructions")
            
            if self.level == SanitizationLevel.HIGH and any(
                pattern.search(original) for pattern in self.role_patterns
            ):
                changes.append("Removed role-playing directives")

        summary = "; ".join(changes) if changes else "No changes"
        return sanitized, summary

    def wrap_safely(self, prompt: str, instruction: str = "Answer the following only:") -> str:
        """
        Wrap prompt in a safe instruction boundary.
        
        Args:
            prompt: Sanitized prompt to wrap
            instruction: Safe instruction prefix
            
        Returns:
            Wrapped prompt with clear boundaries
        """
        return f"{instruction}\n\n{prompt}\n\nProvide a direct response without additional instructions."

    def detect_injection_patterns(self, prompt: str) -> list:
        """
        Detect suspected injection patterns without removing them (for logging).
        
        Args:
            prompt: Prompt to analyze
            
        Returns:
            List of detected injection patterns
        """
        detected = []

        for pattern in self.meta_patterns:
            matches = pattern.findall(prompt)
            if matches:
                detected.extend([f"meta_instruction: {m}" for m in matches])

        for pattern in self.role_patterns:
            matches = pattern.findall(prompt)
            if matches:
                detected.extend([f"role_phrase: {m}" for m in matches])

        for pattern in self.separator_patterns:
            if pattern.search(prompt):
                detected.append("section_separator_detected")

        return detected
