"""Azure OpenAI authentication policy for Azure and Hetzner runtimes."""

from __future__ import annotations

import pytest
from azure import identity

from app.llm_models import LLMProvider
from app.services import llm_client


@pytest.fixture(autouse=True)
def _clear_azure_credential_cache():
    llm_client._azure_credential.cache_clear()
    yield
    llm_client._azure_credential.cache_clear()


def test_client_certificate_mode_is_recognized_as_configured(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    certificate = tmp_path / "azure-client.pem"
    certificate.write_text("not-a-real-certificate")
    certificate.chmod(0o400)
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-enterprise")
    monkeypatch.setenv("AZURE_OPENAI_AUTH", "client_certificate")
    monkeypatch.setenv("AZURE_TENANT_ID", "tenant-id")
    monkeypatch.setenv("AZURE_CLIENT_ID", "client-id")
    monkeypatch.setenv("AZURE_CLIENT_CERTIFICATE_PATH", str(certificate))

    assert llm_client.is_provider_configured(LLMProvider.AZURE_OPENAI) is True


def test_client_certificate_constructs_supported_azure_credential(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    certificate = tmp_path / "azure-client.pem"
    certificate.write_bytes(b"private-certificate-material")
    certificate.chmod(0o400)
    monkeypatch.setenv("AZURE_OPENAI_AUTH", "client_certificate")
    monkeypatch.setenv("AZURE_TENANT_ID", "tenant-id")
    monkeypatch.setenv("AZURE_CLIENT_ID", "client-id")
    monkeypatch.setenv("AZURE_CLIENT_CERTIFICATE_PATH", str(certificate))
    captured: dict[str, object] = {}
    credential = object()

    def fake_certificate_credential(**kwargs):
        captured.update(kwargs)
        return credential

    monkeypatch.setattr(identity, "CertificateCredential", fake_certificate_credential)

    assert llm_client._azure_credential() is credential
    assert captured == {
        "tenant_id": "tenant-id",
        "client_id": "client-id",
        "certificate_data": b"private-certificate-material",
        "send_certificate_chain": True,
    }


def test_client_certificate_rejects_public_file_permissions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    certificate = tmp_path / "azure-client.pem"
    certificate.write_text("not-a-real-certificate")
    certificate.chmod(0o644)
    monkeypatch.setenv("AZURE_OPENAI_AUTH", "client_certificate")
    monkeypatch.setenv("AZURE_TENANT_ID", "tenant-id")
    monkeypatch.setenv("AZURE_CLIENT_ID", "client-id")
    monkeypatch.setenv("AZURE_CLIENT_CERTIFICATE_PATH", str(certificate))

    with pytest.raises(llm_client.LLMConfigurationError, match="0600/0400"):
        llm_client._azure_credential()

    assert llm_client.is_provider_configured(LLMProvider.AZURE_OPENAI) is False


def test_client_certificate_rejects_symlink(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    target = tmp_path / "azure-client-target.pem"
    target.write_text("not-a-real-certificate")
    target.chmod(0o400)
    certificate = tmp_path / "azure-client.pem"
    certificate.symlink_to(target)
    monkeypatch.setenv("AZURE_OPENAI_AUTH", "client_certificate")
    monkeypatch.setenv("AZURE_TENANT_ID", "tenant-id")
    monkeypatch.setenv("AZURE_CLIENT_ID", "client-id")
    monkeypatch.setenv("AZURE_CLIENT_CERTIFICATE_PATH", str(certificate))

    with pytest.raises(llm_client.LLMConfigurationError, match="not a symlink"):
        llm_client._azure_credential()


def test_client_certificate_rejects_empty_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    certificate = tmp_path / "azure-client.pem"
    certificate.touch(mode=0o400)
    monkeypatch.setenv("AZURE_OPENAI_AUTH", "client_certificate")
    monkeypatch.setenv("AZURE_TENANT_ID", "tenant-id")
    monkeypatch.setenv("AZURE_CLIENT_ID", "client-id")
    monkeypatch.setenv("AZURE_CLIENT_CERTIFICATE_PATH", str(certificate))

    with pytest.raises(llm_client.LLMConfigurationError, match="non-empty regular file"):
        llm_client._azure_credential()


def test_production_azure_endpoint_must_use_official_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_ENV", "production")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://attacker.example")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-enterprise")
    monkeypatch.setenv("AZURE_OPENAI_AUTH", "managed_identity")

    assert llm_client.is_provider_configured(LLMProvider.AZURE_OPENAI) is False
    with pytest.raises(llm_client.LLMConfigurationError, match="approved Azure OpenAI"):
        llm_client._azure_openai_base()


def test_azure_endpoint_rejects_credentials_and_query_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "AZURE_OPENAI_ENDPOINT",
        "https://user:password@example.openai.azure.com?api-key=secret",
    )

    with pytest.raises(llm_client.LLMConfigurationError, match="bare HTTP"):
        llm_client._azure_openai_base()


def test_production_azure_endpoint_rejects_nonstandard_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_ENV", "production")
    monkeypatch.setenv(
        "AZURE_OPENAI_ENDPOINT",
        "https://example.openai.azure.com:8443",
    )

    with pytest.raises(llm_client.LLMConfigurationError, match="approved Azure OpenAI"):
        llm_client._azure_openai_base()
