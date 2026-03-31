"""Rule-based classifier for sensitive / prohibited AI Act topics.

Conservative design: any keyword match flags the query as sensitive.
Policy decisions (escalate vs. refuse) happen in the agent node, not here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_PROHIBITED_KEYWORDS: frozenset[str] = frozenset(
    {
        "social scoring",
        "sozialkredit",
        "sozialpunktesystem",
        "massenüberwachung",
        "predictive policing",
    }
)

_SENSITIVE_KEYWORDS: frozenset[str] = frozenset(
    {
        "biometrisch",
        "biometrie",
        "gesichtserkennung",
        "emotionserkennung",
        "emotion recognition",
        "arbeitnehmerüberwachung",
        "mitarbeiterüberwachung",
        "workforce surveillance",
        "biometric categorization",
        "biometrische kategorisierung",
        "subliminal",
        "unterschwellig",
        "manipulation",
        "deepfake",
    }
)

_SENSITIVE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"biometrisch\w*\s+kategori", re.IGNORECASE),
    re.compile(r"emotion\w*\s*erkennung", re.IGNORECASE),
    re.compile(r"workforce\s+surveillance", re.IGNORECASE),
    re.compile(r"arbeitnehmer\w*berwachung", re.IGNORECASE),
]


@dataclass(frozen=True)
class SensitiveTopicResult:
    is_sensitive: bool
    is_prohibited: bool
    matched_rule_id: str
    matched_term: str


_SAFE = SensitiveTopicResult(
    is_sensitive=False,
    is_prohibited=False,
    matched_rule_id="",
    matched_term="",
)


def check_sensitive_topic(query: str) -> SensitiveTopicResult:
    """Check whether a query touches a sensitive or prohibited topic.

    Returns a frozen result with the matched rule for audit logging.
    """
    lower = query.lower()
    tokens = set(re.findall(r"\w+", lower))

    for kw in _PROHIBITED_KEYWORDS:
        kw_tokens = set(kw.split())
        if kw_tokens.issubset(tokens) or kw in lower:
            return SensitiveTopicResult(
                is_sensitive=True,
                is_prohibited=True,
                matched_rule_id="prohibited_topic",
                matched_term=kw,
            )

    for kw in _SENSITIVE_KEYWORDS:
        kw_tokens = set(kw.split())
        if kw_tokens.issubset(tokens) or kw in lower:
            return SensitiveTopicResult(
                is_sensitive=True,
                is_prohibited=False,
                matched_rule_id="sensitive_keyword",
                matched_term=kw,
            )

    for pat in _SENSITIVE_PATTERNS:
        m = pat.search(query)
        if m:
            return SensitiveTopicResult(
                is_sensitive=True,
                is_prohibited=False,
                matched_rule_id="sensitive_pattern",
                matched_term=m.group(0),
            )

    return _SAFE
