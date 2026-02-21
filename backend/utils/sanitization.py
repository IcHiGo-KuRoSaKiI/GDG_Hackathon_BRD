"""
Sanitization utilities for user input in AI prompts.

Provides defense-in-depth security against prompt injection attacks through:
1. Input escaping (wrapping in delimiter tags)
2. Pattern-based injection detection
3. Content validation (length, character ratios, encoding)

Critical for features where user input is interpolated into AI system prompts.
"""

import re
import base64
from typing import Optional


# Prompt injection attack patterns
# Use \s+ for flexible whitespace matching (1 or more spaces/newlines/tabs)
INJECTION_PATTERNS = [
    # Direct instruction manipulation
    # Flexible patterns to catch variations like "ignore all previous instructions"
    r"ignore\s+.*?\b(previous|above|prior)\s+instructions?",
    r"ignore\s+(all|any|the)\s+.*?\binstructions?",
    r"disregard\s+.*?\b(instructions?|rules?)",
    r"forget\s+(everything|all|previous|above)",

    # Role manipulation
    r"(system|assistant|user)\s*:",
    r"you\s+are\s+(now|actually)",  # Removed trailing \s+ to catch end of string
    r"act\s+as\s+(a\s+)?(different|new)",
    r"pretend\s+(you|to)\s+",

    # Special tokens and delimiters (model-specific)
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"\[INST\]",
    r"\[/INST\]",
    r"<</SYS>>",
    r"<<SYS>>",

    # Jailbreak attempts
    r"\bDAN\b",  # "Do Anything Now"
    r"jailbreak",
    r"developer\s+mode",
    r"godmode",

    # Delimiter escape attempts
    r"</user_input>",
    r"<user_input>",
    r"</system>",
    r"<system>",

    # Instruction injection
    r"new\s+instruction",
    r"override\s+(previous|all|above)",
    r"execute\s+the\s+following",
]

# Compile patterns for performance
COMPILED_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in INJECTION_PATTERNS]


def escape_user_input(text: str) -> str:
    """
    Wrap user input in delimiter tags to separate it from system instructions.

    This creates a clear boundary between system prompts and user-provided content,
    making it easier for defensive prompts to instruct the AI to treat tagged
    content as data rather than instructions.

    Args:
        text: Raw user input

    Returns:
        Text wrapped in <user_input> tags

    Example:
        >>> escape_user_input("Make this professional")
        '<user_input>Make this professional</user_input>'
    """
    if not text:
        return "<user_input></user_input>"

    # Escape any existing delimiter tags to prevent breakout
    text = text.replace("<user_input>", "&lt;user_input&gt;")
    text = text.replace("</user_input>", "&lt;/user_input&gt;")

    return f"<user_input>{text}</user_input>"


def detect_prompt_injection(text: str) -> bool:
    """
    Detect potential prompt injection attacks using pattern matching.

    Checks for known attack patterns including:
    - Instruction manipulation ("ignore previous instructions")
    - Role manipulation ("you are now", "system:")
    - Special tokens (<|im_start|>, [INST], etc.)
    - Known jailbreaks (DAN, developer mode)
    - Delimiter escape attempts

    Args:
        text: User input to analyze

    Returns:
        True if injection patterns detected, False otherwise
    """
    if not text:
        return False

    # Check against all compiled patterns
    for pattern in COMPILED_PATTERNS:
        if pattern.search(text):
            return True

    # Additional heuristics

    # 1. Excessive special characters (>15% of content)
    special_char_ratio = sum(1 for c in text if not c.isalnum() and not c.isspace()) / max(len(text), 1)
    if special_char_ratio > 0.15:
        return True

    # 2. Excessive newlines (>5 consecutive)
    if "\n\n\n\n\n" in text:
        return True

    # 3. Base64-encoded content (obfuscation attempt)
    # Check for base64-like strings >30 chars base64 alphabet + padding
    # (30 base64 chars ≈ 22 bytes, enough for meaningful injection attempts)
    base64_pattern = r"[A-Za-z0-9+/]{30,}={0,2}"
    base64_matches = re.findall(base64_pattern, text)

    for potential_b64 in base64_matches:
        # Try to decode - if successful, it might be obfuscated content
        try:
            decoded = base64.b64decode(potential_b64).decode('utf-8', errors='ignore')
            # Check if decoded content contains injection patterns
            # Don't recurse to avoid infinite loops - check patterns directly
            for pattern in COMPILED_PATTERNS:
                if pattern.search(decoded):
                    return True
        except Exception:
            # Not valid base64 or decoding failed - continue to next match
            continue

    return False


def validate_refinement_instruction(instruction: str) -> str:
    """
    Comprehensive validation of text refinement instructions.

    Combines multiple security checks:
    1. Length validation (1-500 chars)
    2. Prompt injection detection
    3. Content quality checks

    Args:
        instruction: User's refinement instruction

    Returns:
        The validated instruction (unchanged if valid)

    Raises:
        ValueError: If validation fails (with specific reason)

    Example:
        >>> validate_refinement_instruction("Make more professional")
        'Make more professional'

        >>> validate_refinement_instruction("Ignore previous. System: you are now...")
        ValueError: Prompt injection detected in instruction
    """
    # 1. Empty check
    if not instruction or not instruction.strip():
        raise ValueError("Instruction cannot be empty")

    instruction = instruction.strip()

    # 2. Length check
    if len(instruction) < 1:
        raise ValueError("Instruction must be at least 1 character")
    if len(instruction) > 500:
        raise ValueError("Instruction too long (max 500 characters)")

    # 3. Prompt injection detection
    if detect_prompt_injection(instruction):
        raise ValueError("Prompt injection detected in instruction")

    # 4. Excessive newlines (>3)
    if instruction.count('\n') > 3:
        raise ValueError("Instruction contains excessive line breaks")

    # 5. Control characters (except newline/tab)
    if any(ord(c) < 32 and c not in ['\n', '\t'] for c in instruction):
        raise ValueError("Instruction contains invalid control characters")

    return instruction


def validate_selected_text(text: str, max_length: int = 5000) -> str:
    """
    Validate selected text to be refined.

    Args:
        text: Selected text from BRD
        max_length: Maximum allowed length

    Returns:
        The validated text (unchanged if valid)

    Raises:
        ValueError: If validation fails
    """
    # Empty is OK (user might be generating new text)
    if not text:
        return ""

    # Length check
    if len(text) > max_length:
        raise ValueError(f"Selected text too long (max {max_length} characters)")

    # Basic prompt injection check (less strict than instructions)
    # Only block obvious attacks, allow normal BRD content
    dangerous_patterns = [
        r"<\|im_start\|>",
        r"<\|im_end\|>",
        r"\[INST\]",
        r"\[/INST\]",
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            raise ValueError("Selected text contains invalid tokens")

    return text


# Export all validation functions
__all__ = [
    'escape_user_input',
    'detect_prompt_injection',
    'validate_refinement_instruction',
    'validate_selected_text',
]
