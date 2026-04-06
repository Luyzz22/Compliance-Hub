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
import json
import os
import sys
import urllib.error
import urllib.request


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

    url = (
        f"{args.api_url.rstrip('/')}/api/v1/ai-systems"
        f"/{args.system_id}/deployment-check"
        f"?caller_type=ci"
    )
    if args.tenant_id:
        url += f"&tenant_id={args.tenant_id}"

    headers: dict[str, str] = {"Accept": "application/json"}
    if args.api_key:
        headers["Authorization"] = f"Bearer {args.api_key}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        print(f"::error::API returned {exc.code}: {exc.reason}", file=sys.stderr)
        return 2
    except Exception as exc:
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
