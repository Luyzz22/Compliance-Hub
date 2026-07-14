from app.security import AuthContext, secret_matches_any
from app.security_credentials import pseudonymous_subject


def test_auth_context_exposes_only_fingerprinted_audit_subject() -> None:
    raw = "a-secret-bearer-credential"
    context = AuthContext(tenant_id="tenant-a", api_key=raw)

    assert context.actor_id.startswith("api_key:sha256:")
    assert raw not in context.actor_id
    assert context.actor_id == AuthContext(tenant_id="tenant-b", api_key=raw).actor_id


def test_secret_matches_any_rejects_blank_and_accepts_exact_match() -> None:
    assert secret_matches_any("candidate", ["other", "candidate"])
    assert not secret_matches_any("", [""])
    assert not secret_matches_any("candidate", ["Candidate"])


def test_direct_identifier_uses_keyed_pseudonym_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_AUDIT_PSEUDONYMIZATION_KEY", "k" * 32)

    subject = pseudonymous_subject("email", "Person@Example.com")

    assert subject.startswith("email:hmac-sha256:")
    assert "person@example.com" not in subject
    assert subject == pseudonymous_subject("email", " person@example.com ")
