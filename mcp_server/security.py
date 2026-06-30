import re


def redact_pii(text: str) -> str:
    """Masks credit card-like number sequences (e.g., 13 to 19 digits) as [REDACTED-CC]."""
    if not text:
        return text
    # Match sequences of 13 to 19 digits, possibly separated by spaces or hyphens
    pattern = r"\b(?:\d[ -]*?){13,19}\b"
    return re.sub(pattern, "[REDACTED-CC]", text)


def screen_for_injection(text: str) -> str:
    """Detects suspicious instructional phrases and replaces with a warning."""
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
