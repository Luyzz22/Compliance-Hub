"""Credential primitives shared by identity and API authentication.

Opaque verification/reset tokens carry enough entropy to be looked up by a
deterministic SHA-256 digest. Only the digest is persisted, so a database read
does not immediately disclose usable bearer credentials.
"""

from __future__ import annotations

import hashlib
import hmac
import os

_OPAQUE_DIGEST_PREFIX = "sha256$"


def hash_opaque_token(raw_token: str) -> str:
    """Return the canonical at-rest representation for a high-entropy token."""
    token = str(raw_token).strip()
    if not token:
        raise ValueError("token must not be empty")
    return f"{_OPAQUE_DIGEST_PREFIX}{hashlib.sha256(token.encode('utf-8')).hexdigest()}"


def opaque_token_lookup_candidates(raw_token: str) -> tuple[str, ...]:
    """Return hashed lookup plus legacy plaintext value for rolling migration."""
    token = str(raw_token).strip()
    if not token:
        return ()
    if token.startswith(_OPAQUE_DIGEST_PREFIX):
        return (token,)
    return (hash_opaque_token(token), token)


def pseudonymous_subject(namespace: str, value: str) -> str:
    """Return a stable pseudonym; production requires an operator-controlled HMAC key."""
    normalized_namespace = str(namespace).strip().lower() or "subject"
    normalized_value = str(value).strip().lower()
    key = os.getenv("COMPLIANCEHUB_AUDIT_PSEUDONYMIZATION_KEY", "").encode("utf-8")
    if key:
        digest = hmac.new(key, normalized_value.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{normalized_namespace}:hmac-sha256:{digest[:16]}"
    digest = hashlib.sha256(normalized_value.encode("utf-8")).hexdigest()
    return f"{normalized_namespace}:dev-sha256:{digest[:16]}"
