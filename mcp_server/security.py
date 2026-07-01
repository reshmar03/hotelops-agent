"""Security Utility Functions for Data Sanitization.

This module implements the Layer 1 security boundary (MCP data boundary).
Filtering raw data *before* it leaves the MCP server ensures that sensitive PII
or malicious prompt injection strings never enter the LLM's context window.
This prevents data leakage in agent logs and protects the model from indirect
prompt injection attacks embedded in guest comment fields.
"""

import re


def redact_pii(text: str) -> str:
    """Masks credit card-like sequences (13 to 19 digits) as [REDACTED-CC].

    This regex identifies typical card number patterns, allowing dashes/spaces,
    and replaces them. Sanitizing this at the MCP boundary guarantees the model
    never sees or stores raw payment card data in its context.
    """
    if not text:
        return text
    # Match sequences of 13 to 19 digits, possibly separated by spaces or hyphens
    pattern = r"\b(?:\d[ -]*?){13,19}\b"
    return re.sub(pattern, "[REDACTED-CC]", text)


def screen_for_injection(text: str) -> str:
    """Detects suspicious indirect instructional phrases in user comments.

    If a known attack phrase (e.g. 'ignore previous instructions') is found,
    the entire comment string is replaced with a warning flag block. This hard
    withholding is a robust guardrail that stops the LLM from executing 
    arbitrary instructions masqueraded as guest comments.
    """
    if not text:
        return text

    suspicious_phrases = [
        "ignore previous instructions",
        "bypass",
        "upgrade me for free",
    ]

    lower_text = text.lower()
    for phrase in suspicious_phrases:
        if phrase in lower_text:
            return "[FLAGGED: potential prompt injection — original withheld]"

    return text
