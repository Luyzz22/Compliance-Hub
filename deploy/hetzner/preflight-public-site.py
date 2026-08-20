#!/usr/bin/env python3
"""Preflight für die öffentliche Website (Profil `public_site`).

Prüft die Container-Umgebungsdatei, bevor auf dem Server irgendetwas gestartet
wird. Das Release-Gate im Image prüft dieselben Invarianten beim Containerstart
— dort aber erst, wenn Server, TLS und DNS bereits stehen. Dieses Skript zieht
die Prüfung nach vorn und benennt jede Abweichung einzeln.

Aufruf:
    python3 deploy/hetzner/preflight-public-site.py deploy/hetzner/.env.public-site

Optional zusätzlich die Compose-Substitutionsdatei:
    python3 deploy/hetzner/preflight-public-site.py .env.public-site --compose-env .env

Exit 0 = ausrollbar, Exit 1 = Befund. Keine Netzwerkzugriffe, keine Secrets.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

# Spiegelt `allowedComplianceHubKeys` in
# frontend/scripts/verify-enterprise-readiness.mjs für das public_site-Profil.
LEGAL_REQUIRED = [
    "COMPLIANCEHUB_APP_ORIGIN",
    "COMPLIANCEHUB_TRUSTED_HOSTS",
    "COMPLIANCEHUB_LEGAL_ENTITY_NAME",
    "COMPLIANCEHUB_LEGAL_REPRESENTATIVE",
    "COMPLIANCEHUB_LEGAL_STREET",
    "COMPLIANCEHUB_LEGAL_POSTAL_CODE",
    "COMPLIANCEHUB_LEGAL_CITY",
    "COMPLIANCEHUB_LEGAL_COUNTRY",
    "COMPLIANCEHUB_LEGAL_EMAIL",
    "COMPLIANCEHUB_LEGAL_REGISTER_COURT",
    "COMPLIANCEHUB_LEGAL_REGISTER_NUMBER",
    "COMPLIANCEHUB_LEGAL_VAT_ID",
    "COMPLIANCEHUB_PRIVACY_EMAIL",
    "COMPLIANCEHUB_PRIVACY_NOTICE_VERSION",
    "COMPLIANCEHUB_PRIVACY_REVIEWED_AT",
    "COMPLIANCEHUB_PRIVACY_LOG_RETENTION_DAYS",
    "COMPLIANCEHUB_PRIVACY_LEAD_RETENTION_DAYS",
    "COMPLIANCEHUB_SECURITY_CONTACT",
]

ALLOWED_KEYS = set(LEGAL_REQUIRED) | {
    "COMPLIANCEHUB_RELEASE_CHANNEL",
    "COMPLIANCEHUB_RELEASE_PROFILE",
    "COMPLIANCEHUB_PUBLIC_SITE_READY",
    "COMPLIANCEHUB_PUBLIC_DEMO_ENABLED",
    "COMPLIANCEHUB_PUBLIC_LEAD_CAPTURE_ENABLED",
    "COMPLIANCEHUB_ENTRA_ENABLED",
    "COMPLIANCEHUB_CSP_REPORTING_READY",
    "COMPLIANCEHUB_LEGAL_PHONE",
    "COMPLIANCEHUB_LEGAL_PUBLISH_READY",
    "COMPLIANCEHUB_PRIVACY_DPO_CONTACT",
    "COMPLIANCEHUB_LLM_PII_MODE",
    "COMPLIANCEHUB_RUNTIME_PREFLIGHT",
}

MUST_STAY_DISABLED = [
    "COMPLIANCEHUB_PUBLIC_DEMO_ENABLED",
    "COMPLIANCEHUB_PUBLIC_LEAD_CAPTURE_ENABLED",
    "COMPLIANCEHUB_ENTRA_ENABLED",
    "COMPLIANCEHUB_CSP_REPORTING_READY",
]

FORBIDDEN_PREFIXES = ("POSTGRES_", "SUPABASE_", "AZURE_", "NEXT_PUBLIC_", "VERCEL")
FORBIDDEN_EXACT = {"DATABASE_URL", "PGPASSWORD"}
PLACEHOLDER = re.compile(r"(?:replace-after|replace-with|change-?me|todo|tbd|your-)", re.I)


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def check_container_env(env: dict[str, str]) -> list[str]:
    findings: list[str] = []

    for key in LEGAL_REQUIRED:
        if not env.get(key):
            findings.append(f"{key} fehlt oder ist leer")

    for key, value in env.items():
        if not value:
            continue
        if key.startswith("COMPLIANCEHUB_") and key not in ALLOWED_KEYS:
            findings.append(
                f"{key} steht nicht auf der Allowlist des public_site-Profils "
                "— der Containerstart würde abbrechen"
            )
        if key in FORBIDDEN_EXACT or key.startswith(FORBIDDEN_PREFIXES):
            findings.append(f"{key} ist im zustandslosen public_site-Release verboten")
        if key in LEGAL_REQUIRED and PLACEHOLDER.search(value):
            findings.append(f"{key} enthält noch einen Platzhalter: {value!r}")

    if env.get("COMPLIANCEHUB_RELEASE_PROFILE") != "public_site":
        findings.append("COMPLIANCEHUB_RELEASE_PROFILE muss public_site sein")
    if env.get("COMPLIANCEHUB_RELEASE_CHANNEL") != "production":
        findings.append("COMPLIANCEHUB_RELEASE_CHANNEL muss production sein")
    if env.get("COMPLIANCEHUB_PUBLIC_SITE_READY") != "true":
        findings.append(
            "COMPLIANCEHUB_PUBLIC_SITE_READY muss den geprüften Release attestieren (true)"
        )
    if env.get("COMPLIANCEHUB_LEGAL_PUBLISH_READY") != "true":
        findings.append(
            "COMPLIANCEHUB_LEGAL_PUBLISH_READY muss nach dokumentierter "
            "rechtlicher Prüfung true sein"
        )

    for key in MUST_STAY_DISABLED:
        if env.get(key) == "true":
            findings.append(f"{key} muss im public_site-Release deaktiviert bleiben")

    if env.get("COMPLIANCEHUB_APP_ORIGIN") and (
        env["COMPLIANCEHUB_APP_ORIGIN"] != "https://complywithai.de"
    ):
        findings.append(
            "COMPLIANCEHUB_APP_ORIGIN muss im public_site-Profil https://complywithai.de sein"
        )

    hosts = {
        host.strip().lower()
        for host in env.get("COMPLIANCEHUB_TRUSTED_HOSTS", "").split(",")
        if host.strip()
    }
    if hosts and "complywithai.de" not in hosts:
        findings.append("COMPLIANCEHUB_TRUSTED_HOSTS muss den Anwendungshost enthalten")

    if env.get("COMPLIANCEHUB_LEGAL_COUNTRY") == "Deutschland":
        postal = env.get("COMPLIANCEHUB_LEGAL_POSTAL_CODE", "")
        if postal and not re.fullmatch(r"\d{5}", postal):
            findings.append("COMPLIANCEHUB_LEGAL_POSTAL_CODE muss fünfstellig sein")
        vat = env.get("COMPLIANCEHUB_LEGAL_VAT_ID", "")
        if vat and not re.fullmatch(r"DE\d{9}", vat):
            findings.append("COMPLIANCEHUB_LEGAL_VAT_ID muss dem Format DE + 9 Ziffern folgen")

    for key in ("COMPLIANCEHUB_LEGAL_EMAIL", "COMPLIANCEHUB_PRIVACY_EMAIL"):
        value = env.get(key, "")
        if value and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            findings.append(f"{key} muss eine gültige E-Mail-Adresse sein")

    contact = env.get("COMPLIANCEHUB_SECURITY_CONTACT", "")
    if contact and not contact.startswith(("https://", "mailto:")):
        findings.append("COMPLIANCEHUB_SECURITY_CONTACT muss eine HTTPS- oder mailto-Adresse sein")

    reviewed = env.get("COMPLIANCEHUB_PRIVACY_REVIEWED_AT", "")
    if reviewed:
        try:
            reviewed_date = dt.date.fromisoformat(reviewed)
        except ValueError:
            findings.append("COMPLIANCEHUB_PRIVACY_REVIEWED_AT muss YYYY-MM-DD sein")
        else:
            today = dt.date.today()
            if reviewed_date > today:
                findings.append(
                    "COMPLIANCEHUB_PRIVACY_REVIEWED_AT darf nicht in der Zukunft liegen"
                )
            elif (today - reviewed_date).days > 366:
                findings.append(
                    "Die Datenschutzerklärung muss mindestens jährlich erneut geprüft werden"
                )

    for key, low, high in (
        ("COMPLIANCEHUB_PRIVACY_LOG_RETENTION_DAYS", 1, 365),
        ("COMPLIANCEHUB_PRIVACY_LEAD_RETENTION_DAYS", 1, 3650),
    ):
        value = env.get(key, "")
        if value and (not value.isdigit() or not low <= int(value) <= high):
            findings.append(f"{key} muss zwischen {low} und {high} liegen")

    return findings


def check_compose_env(env: dict[str, str]) -> list[str]:
    findings: list[str] = []

    image = env.get("COMPLIANCEHUB_FRONTEND_IMAGE", "")
    if not image:
        findings.append("COMPLIANCEHUB_FRONTEND_IMAGE fehlt")
    elif "@sha256:" not in image:
        findings.append(
            "COMPLIANCEHUB_FRONTEND_IMAGE muss einen unveränderlichen Digest "
            "tragen (…@sha256:…), keinen beweglichen Tag"
        )

    for key in (
        "COMPLIANCEHUB_PUBLIC_HOST",
        "COMPLIANCEHUB_RELEASE_ID",
        "COMPLIANCEHUB_RELEASE_COMMIT",
    ):
        if not env.get(key):
            findings.append(f"{key} fehlt")

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("env_file", type=Path, help="Container-Umgebungsdatei")
    parser.add_argument(
        "--compose-env",
        type=Path,
        default=None,
        help="Optionale Compose-Substitutionsdatei (.env)",
    )
    args = parser.parse_args()

    if not args.env_file.is_file():
        print(f"Datei nicht gefunden: {args.env_file}", file=sys.stderr)
        return 1

    findings = check_container_env(read_env(args.env_file))
    scope = [f"Container-Umgebung: {args.env_file}"]

    if args.compose_env:
        if not args.compose_env.is_file():
            print(f"Datei nicht gefunden: {args.compose_env}", file=sys.stderr)
            return 1
        findings += check_compose_env(read_env(args.compose_env))
        scope.append(f"Compose-Substitution: {args.compose_env}")

    for line in scope:
        print(line)

    if findings:
        print(f"\nPreflight fehlgeschlagen — {len(findings)} Befund(e):", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding}", file=sys.stderr)
        return 1

    print("\nPreflight bestanden: Die Konfiguration erfüllt das public_site-Profil.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
