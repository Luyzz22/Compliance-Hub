from __future__ import annotations

import pytest

from scripts.ci.check_ai_system_readiness import build_api_endpoint


def test_readiness_endpoint_encodes_untrusted_path_and_query_values() -> None:
    endpoint = build_api_endpoint(
        "https://api.complywithai.de/base",
        "system/../../other?admin=true",
        "tenant&caller_type=browser",
    )

    assert endpoint.scheme == "https"
    assert endpoint.host == "api.complywithai.de"
    assert endpoint.target == (
        "/base/api/v1/ai-systems/system%2F..%2F..%2Fother%3Fadmin%3Dtrue/deployment-check"
        "?caller_type=ci&tenant_id=tenant%26caller_type%3Dbrowser"
    )


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://api.example.com",
        "https://user:password@api.example.com",
        "https://api.example.com?redirect=https://attacker.example",
        "https://api.example.com#fragment",
    ],
)
def test_readiness_endpoint_rejects_unsafe_base_urls(url: str) -> None:
    with pytest.raises(ValueError):
        build_api_endpoint(url, "system-1", "tenant-1")


def test_readiness_endpoint_allows_loopback_http_for_local_ci() -> None:
    endpoint = build_api_endpoint("http://127.0.0.1:8000", "system-1", "")

    assert endpoint.port == 8000
    assert endpoint.target.endswith("?caller_type=ci")
