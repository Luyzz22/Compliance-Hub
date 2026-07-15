#!/usr/bin/env python3
"""CI helper: check AI system deployment readiness via ComplianceHub API.

Usage:
    python scripts/ci/check_ai_system_readiness.py \\
        --system-id SAP-CREDIT-AI-01 \\
        --tenant-id acme-gmbh \\
        --api-url http://localhost:8000

Exit codes:
    0  — readiness OK (ready_for_review or partially_covered for non-HRC)
    1  — high_risk_candidate with insufficient_evidence (strong warning)
    2  — system not found or API error

Environment variables (alternative to CLI args):
    COMPLIANCEHUB_API_URL
    COMPLIANCEHUB_TENANT_ID
    COMPLIANCEHUB_API_KEY

Example GitHub Actions step:
    - name: Check AI System Readiness
      run: |
        python scripts/ci/check_ai_system_readiness.py \\
          --system-id ${{ env.AI_SYSTEM_ID }} \\
          --tenant-id ${{ secrets.TENANT_ID }} \\
          --api-url ${{ secrets.COMPLIANCEHUB_API_URL }}
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import sys
from dataclasses import dataclass
from urllib.parse import quote, urlencode, urlsplit

MAX_RESPONSE_BYTES = 1024 * 1024
LOCAL_HTTP_HOSTS = {"localhost", "127.0.0.1", "::1"}


@dataclass(frozen=True)
class ApiEndpoint:
    scheme: str
    host: str
    port: int | None
    target: str


class ApiResponseError(RuntimeError):
    def __init__(self, status: int, reason: str) -> None:
        super().__init__(f"API returned {status}: {reason}")
        self.status = status
        self.reason = reason


def build_api_endpoint(api_url: str, system_id: str, tenant_id: str) -> ApiEndpoint:
    parsed = urlsplit(api_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("API URL must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("API URL must not contain credentials, query parameters or fragments")
    if parsed.scheme == "http" and parsed.hostname.lower() not in LOCAL_HTTP_HOSTS:
        raise ValueError("Plain HTTP is permitted only for local development")

    base_path = parsed.path.rstrip("/")
    path = f"{base_path}/api/v1/ai-systems/{quote(system_id, safe='')}/deployment-check"
    query: dict[str, str] = {"caller_type": "ci"}
    if tenant_id:
        query["tenant_id"] = tenant_id
    return ApiEndpoint(
        scheme=parsed.scheme,
        host=parsed.hostname,
        port=parsed.port,
        target=f"{path}?{urlencode(query)}",
    )


def request_json(endpoint: ApiEndpoint, headers: dict[str, str]) -> dict[str, object]:
    connection_type = (
        http.client.HTTPSConnection if endpoint.scheme == "https" else http.client.HTTPConnection
    )
    connection = connection_type(endpoint.host, endpoint.port, timeout=30)
    try:
        connection.request("GET", endpoint.target, headers=headers)
        response = connection.getresponse()
        if response.status < 200 or response.status >= 300:
            raise ApiResponseError(response.status, response.reason)
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("API response exceeds the 1 MiB safety limit")
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("API response must be a JSON object")
        return payload
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Check AI system deployment readiness")
    parser.add_argument("--system-id", required=True)
    parser.add_argument(
        "--tenant-id",
        default=os.environ.get("COMPLIANCEHUB_TENANT_ID", ""),
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("COMPLIANCEHUB_API_URL", "http://localhost:8000"),
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("COMPLIANCEHUB_API_KEY", ""),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=("Exit 1 for any blocking items (not just HRC+insufficient)"),
    )
    args = parser.parse_args()

    headers: dict[str, str] = {"Accept": "application/json"}
    if args.api_key:
        headers["Authorization"] = f"Bearer {args.api_key}"

    try:
        endpoint = build_api_endpoint(args.api_url, args.system_id, args.tenant_id)
        data = request_json(endpoint, headers)
    except ApiResponseError as exc:
        print(f"::error::API returned {exc.status}: {exc.reason}", file=sys.stderr)
        return 2
    except (
        http.client.HTTPException,
        json.JSONDecodeError,
        OSError,
        UnicodeError,
        ValueError,
    ) as exc:
        print(f"::error::API call failed: {exc}", file=sys.stderr)
        return 2

    level = data.get("readiness_level", "unknown")
    is_hrc = data.get("is_high_risk_candidate", False)
    blocking = data.get("blocking_items", [])
    advisory = data.get("advisory_message_de", "")

    print(f"System:        {args.system_id}")
    print(f"Classification: {data.get('classification', '?')}")
    print(f"Lifecycle:     {data.get('lifecycle_stage', '?')}")
    print(f"Readiness:     {level}")
    print(f"HRC:           {is_hrc}")
    print(f"Blocking:      {len(blocking)} item(s)")
    if advisory:
        print(f"\n{advisory}")

    if is_hrc and level == "insufficient_evidence":
        print(
            "\n::warning::High-risk-candidate system with insufficient "
            "evidence — deployment review strongly recommended.",
            file=sys.stderr,
        )
        return 1

    if args.strict and blocking:
        print(
            f"\n::warning::Strict mode: {len(blocking)} blocking item(s) found.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
