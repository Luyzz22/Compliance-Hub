"""Deployment-wide data-sovereignty mode.

Sovereignty is not a property you assert in marketing copy — it is an operating mode you
enforce and can demonstrate. This module turns ``COMPLIANCEHUB_SOVEREIGNTY_MODE`` into
three things that are actually verifiable:

1. a startup check that refuses to boot when a vendor forbidden in the selected mode is
   configured,
2. an allowlist the LLM router filters its provider chain against — so a US provider is
   removed from the chain rather than merely deprioritised,
3. the set of marketing/trust-center statements that may truthfully be made, exposed
   through the API so a prospect can check them instead of taking our word for it.

Rationale and the full target architecture per mode:
``docs/market-readiness/06-target-architecture-modes.md``.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import StrEnum
from functools import lru_cache
from urllib.parse import urlsplit

from app.outbound_policy import OutboundPolicyError, approved_private_service_base_url

logger = logging.getLogger(__name__)


class SovereigntyMode(StrEnum):
    """Operating mode governing which vendors may sit in the data path."""

    #: No deployment-level restriction. Every provider is permitted and **no** residency
    #: or sovereignty statement may be made. Exists so that an operator who genuinely
    #: wants direct US model APIs has an honest setting instead of quietly weakening a
    #: mode that promises otherwise.
    UNRESTRICTED = "unrestricted"
    #: Hetzner-first DACH mode: Azure is the only documented US-provider exception.
    STANDARD_DACH = "standard_dach"
    #: EU-established providers only; no US-controlled provider in the data path.
    EU_SOVEREIGN = "eu_sovereign"
    #: Customer-controlled or dedicated DE deployment; local inference only.
    STRICT_SOVEREIGN = "strict_sovereign"


#: Providers as named by :class:`app.llm_models.LLMProvider`. Kept as plain strings so
#: this module stays importable from configuration checks without pulling in the LLM
#: stack.
_AZURE = "azure_openai"
_OPENAI = "openai"
_CLAUDE = "claude"
_GEMINI = "gemini"
_LLAMA = "llama"

_DIRECT_US_LLM_ENV_VARS = (
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "CLAUDE_API_KEY",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_API_URL",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "COMPLIANCEHUB_LLM_US_CLOUD_OK",
    "COMPLIANCEHUB_LLM_ASSUME_CLAUDE_EU",
)
_EXTERNAL_TELEMETRY_ENV_VARS = (
    "LANGSMITH_API_KEY",
    "LANGSMITH_ENDPOINT",
    "LANGSMITH_TRACING",
    "LANGCHAIN_API_KEY",
    "LANGCHAIN_ENDPOINT",
    "LANGCHAIN_TRACING_V2",
    "HAYSTACK_TELEMETRY_ENABLED",
    "POSTHOG_API_KEY",
    "POSTHOG_HOST",
)
_FORBIDDEN_EXTERNAL_SERVICE_ENV_VARS = (
    "COMPLIANCEHUB_STRIPE_WEBHOOK_SECRET",
    "COMPLIANCEHUB_STRIPE_WEBHOOK_SECRET_FILE",
    "STRIPE_API_KEY",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "TEMPORAL_API_KEY",
)
_PRODUCTION_DIRECT_SECRET_ENV_VARS = (
    "COMPLIANCEHUB_DB_URL",
    "COMPLIANCEHUB_BFF_SHARED_SECRET",
    "COMPLIANCEHUB_AUDIT_PSEUDONYMIZATION_KEY",
    "COMPLIANCEHUB_N8N_WEBHOOK_SECRET",
    "COMPLIANCEHUB_EXPORT_WEBHOOK_SECRET",
    "INTERNAL_HEALTH_API_KEY",
    "AZURE_OPENAI_API_KEY",
)


@dataclass(frozen=True)
class SovereigntyProfile:
    """What a mode permits, forbids and therefore allows us to claim."""

    mode: SovereigntyMode
    title_de: str
    allowed_llm_providers: frozenset[str]
    #: Environment variables that must not be set (truthy) in this mode.
    forbidden_env_vars: tuple[str, ...] = ()
    permitted_claims_de: tuple[str, ...] = ()
    forbidden_claims_de: tuple[str, ...] = ()
    residual_risks_de: tuple[str, ...] = ()
    subprocessor_jurisdictions: tuple[str, ...] = field(default=())


_PROFILES: dict[SovereigntyMode, SovereigntyProfile] = {
    SovereigntyMode.UNRESTRICTED: SovereigntyProfile(
        mode=SovereigntyMode.UNRESTRICTED,
        title_de="Ohne Residenzbeschränkung",
        allowed_llm_providers=frozenset({_AZURE, _OPENAI, _CLAUDE, _GEMINI, _LLAMA}),
        permitted_claims_de=(),
        forbidden_claims_de=(
            "souverän",
            "EU-only",
            "EU-Hosting",
            "keine US-Anbieter",
            "CLOUD-Act-sicher",
            "DSGVO-konform",
            "Datenresidenz EU",
        ),
        residual_risks_de=(
            "In diesem Modus bestehen keine deployment-seitigen Vendor-Beschränkungen. "
            "Aussagen zu Datenresidenz oder Souveränität sind nicht belegbar.",
        ),
        subprocessor_jurisdictions=("EU", "US", "other"),
    ),
    SovereigntyMode.STANDARD_DACH: SovereigntyProfile(
        mode=SovereigntyMode.STANDARD_DACH,
        title_de="Standard DACH Compliance",
        # Self-hosted inference stays permitted; the point of this mode is to keep
        # direct US LLM APIs out, not to forbid running a model yourself.
        allowed_llm_providers=frozenset({_AZURE, _LLAMA}),
        forbidden_env_vars=(
            _DIRECT_US_LLM_ENV_VARS
            + _EXTERNAL_TELEMETRY_ENV_VARS
            + _FORBIDDEN_EXTERNAL_SERVICE_ENV_VARS
        ),
        permitted_claims_de=(
            "Betrieb in EU-Rechenzentren (Deutschland/EU).",
            "Auftragsverarbeitung nach DSGVO mit dokumentierten Drittlandtransfers "
            "und offengelegten Subprozessoren.",
            "Externe KI-Funktionen standardmäßig deaktiviert; bei Aktivierung "
            "ausschließlich über Azure OpenAI in EU-Regionen.",
        ),
        forbidden_claims_de=(
            "souverän",
            "EU-only",
            "keine US-Anbieter",
            "CLOUD-Act-sicher",
            "DSGVO-konform",
        ),
        residual_risks_de=(
            "Microsoft Corporation ist als dokumentierte Azure-Inferenz- und optionale "
            "Entra-Ausnahme ein US-Unternehmen und unterliegt auch bei Verarbeitung in "
            "EU-Regionen US-Recht.",
        ),
        subprocessor_jurisdictions=("EU", "US"),
    ),
    SovereigntyMode.EU_SOVEREIGN: SovereigntyProfile(
        mode=SovereigntyMode.EU_SOVEREIGN,
        title_de="EU Sovereign",
        allowed_llm_providers=frozenset({_LLAMA}),
        forbidden_env_vars=(
            _DIRECT_US_LLM_ENV_VARS
            + _EXTERNAL_TELEMETRY_ENV_VARS
            + _FORBIDDEN_EXTERNAL_SERVICE_ENV_VARS
        ),
        permitted_claims_de=(
            "Vollständiger Betrieb bei EU-ansässigen Anbietern.",
            "Keine US-kontrollierten Dienstleister im Datenpfad.",
            "KI-Verarbeitung ausschließlich über EU-Anbieter oder vollständig deaktiviert.",
        ),
        forbidden_claims_de=(
            "CLOUD-Act-immun",
            "garantiert kein Behördenzugriff",
            "DSGVO-konform",
        ),
        residual_risks_de=(
            "Auch EU-Anbieter können Muttergesellschaften, Kapitalgeber oder Zulieferer "
            "mit US-Bezug haben; die Eigentümerstruktur der Subprozessoren wird geprüft "
            "und offengelegt.",
        ),
        subprocessor_jurisdictions=("EU",),
    ),
    SovereigntyMode.STRICT_SOVEREIGN: SovereigntyProfile(
        mode=SovereigntyMode.STRICT_SOVEREIGN,
        title_de="Strict Sovereign / Anti-CLOUD-Act",
        allowed_llm_providers=frozenset({_LLAMA}),
        forbidden_env_vars=_DIRECT_US_LLM_ENV_VARS
        + _EXTERNAL_TELEMETRY_ENV_VARS
        + _FORBIDDEN_EXTERNAL_SERVICE_ENV_VARS
        + (
            "COMPLIANCEHUB_LLM_ASSUME_AZURE_EU",
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_API_KEY",
        ),
        permitted_claims_de=(
            "Betrieb ausschließlich in Ihrer Infrastruktur oder in einem dedizierten "
            "deutschen Rechenzentrum.",
            "Keine US-kontrollierten Anbieter im Datenpfad, im Betrieb, im "
            "Schlüsselmanagement, im Support oder im Backup.",
            "KI-Inferenz ausschließlich lokal.",
        ),
        forbidden_claims_de=("CLOUD-Act-immun",),
        residual_risks_de=(
            "Hardware-, Firmware- und Open-Source-Lieferketten enthalten "
            "US-Komponenten; die Software-Stückliste wird offengelegt.",
        ),
        subprocessor_jurisdictions=(),
    ),
}

#: Deliberately the mode that authorises **no** claims.
#:
#: A restrictive default would be the safer-looking choice, but it would have the runtime
#: assert a posture the operator never selected — ``standard_dach`` authorises statements
#: like "Betrieb in EU-Rechenzentren", which nothing in an unconfigured deployment
#: guarantees. It would also silently cut off model providers that a running deployment
#: depends on. A mode that permits marketing statements has to be an explicit decision.
DEFAULT_MODE = SovereigntyMode.UNRESTRICTED


class SovereigntyConfigurationError(RuntimeError):
    """Raised when the runtime configuration contradicts the selected mode."""


def _env_is_truthy(name: str) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return False
    value = raw.strip()
    if not value:
        return False
    # Endpoint-style variables carry a URL rather than a boolean; presence is the signal.
    if value.lower() in {"0", "false", "no", "off"}:
        return False
    return True


def _verify_private_temporal_address() -> list[str]:
    """Validate the optional self-hosted Temporal endpoint without resolving DNS."""

    if not _env_is_truthy("COMPLIANCEHUB_TEMPORAL_ENABLED"):
        return []
    address = os.getenv("TEMPORAL_ADDRESS", "").strip()
    if not address:
        return ["TEMPORAL_ADDRESS is required when Temporal is enabled in production"]
    parsed = urlsplit(f"//{address}")
    try:
        port = parsed.port
    except ValueError:
        port = None
    if (
        not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path
        or parsed.query
        or parsed.fragment
        or port is None
    ):
        return ["TEMPORAL_ADDRESS must be a bare host:port without credentials or parameters"]

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "temporal.io" or hostname.endswith((".temporal.io", ".tmprl.cloud")):
        return ["TEMPORAL_ADDRESS must not target Temporal Cloud in a restrictive profile"]
    allowed = {
        value.strip().rstrip(".").lower()
        for value in os.getenv("COMPLIANCEHUB_TEMPORAL_ALLOWED_HOSTS", "").split(",")
        if value.strip()
    }
    if hostname not in allowed:
        return ["TEMPORAL_ADDRESS host must be listed in COMPLIANCEHUB_TEMPORAL_ALLOWED_HOSTS"]
    return []


@lru_cache
def current_mode() -> SovereigntyMode:
    """Return the configured mode, defaulting to ``unrestricted`` (see ``DEFAULT_MODE``)."""
    raw = os.getenv("COMPLIANCEHUB_SOVEREIGNTY_MODE", "").strip().lower()
    if not raw:
        return DEFAULT_MODE
    try:
        return SovereigntyMode(raw)
    except ValueError:
        known = ", ".join(m.value for m in SovereigntyMode)
        raise SovereigntyConfigurationError(
            f"Unknown COMPLIANCEHUB_SOVEREIGNTY_MODE={raw!r}; expected one of: {known}"
        ) from None


def current_profile() -> SovereigntyProfile:
    """Return the profile for the configured mode."""
    return _PROFILES[current_mode()]


def allowed_llm_providers() -> frozenset[str]:
    """Provider names the LLM router may keep in its fallback chain."""
    return current_profile().allowed_llm_providers


def filter_llm_provider_chain(chain: list[str]) -> list[str]:
    """
    Drop providers the current mode forbids, preserving order.

    Filtering rather than reordering is the point: a chain that merely *prefers* an EU
    provider still falls back to a US one when the preferred call fails, which is
    exactly the situation an EU-residency commitment has to rule out.
    """
    allowed = allowed_llm_providers()
    return [provider for provider in chain if str(provider) in allowed]


def verify_startup_configuration(*, raise_on_error: bool = True) -> list[str]:
    """
    Check the process environment against the selected mode.

    Returns the list of violations. With ``raise_on_error`` (the default, used at
    startup) any violation aborts the process: booting with a forbidden vendor
    configured would silently invalidate every claim the mode authorises.
    """
    profile = current_profile()
    if profile.mode is SovereigntyMode.UNRESTRICTED:
        # Surfaced at every startup: an operator who never chose a mode should not be
        # able to believe a residency posture is in force.
        logger.warning(
            "sovereignty_mode_unrestricted no vendor restrictions are enforced and no "
            "residency or sovereignty statement is permitted; set "
            "COMPLIANCEHUB_SOVEREIGNTY_MODE to standard_dach, eu_sovereign or "
            "strict_sovereign to enforce one"
        )

    violations: list[str] = []
    environment = os.getenv("COMPLIANCEHUB_ENV", "dev").strip().lower()
    if profile.mode is SovereigntyMode.UNRESTRICTED and environment in {"prod", "production"}:
        violations.append(
            "COMPLIANCEHUB_SOVEREIGNTY_MODE must be explicitly restrictive in production; "
            "unrestricted is forbidden"
        )
    if environment in {"prod", "production"}:
        violations.extend(
            f"{name} is a direct secret and is forbidden in production; use a mounted secret file"
            for name in _PRODUCTION_DIRECT_SECRET_ENV_VARS
            if _env_is_truthy(name)
        )
        if not _env_is_truthy("COMPLIANCEHUB_OPA_STRICT_MISSING"):
            violations.append("COMPLIANCEHUB_OPA_STRICT_MISSING must be true in production")
        opa_url = os.getenv("OPA_URL", "").strip()
        if not opa_url:
            violations.append("OPA_URL is required in production")
        else:
            try:
                approved_private_service_base_url(
                    opa_url,
                    allowlist_variable="COMPLIANCEHUB_OPA_ALLOWED_HOSTS",
                )
            except OutboundPolicyError as exc:
                violations.append(f"OPA_URL violates the private-service policy: {exc}")
        violations.extend(_verify_private_temporal_address())

    violations.extend(
        f"{name} is set but forbidden in sovereignty mode '{profile.mode.value}'"
        for name in profile.forbidden_env_vars
        if _env_is_truthy(name)
    )

    if violations and raise_on_error:
        raise SovereigntyConfigurationError(
            "Sovereignty configuration conflict:\n  - " + "\n  - ".join(violations)
        )
    for violation in violations:
        logger.error("sovereignty_violation %s", violation)
    return violations


def public_profile_payload() -> dict[str, object]:
    """Machine-readable profile for the trust center and security questionnaires."""
    profile = current_profile()
    return {
        "mode": profile.mode.value,
        "title_de": profile.title_de,
        "allowed_llm_providers": sorted(profile.allowed_llm_providers),
        "permitted_claims_de": list(profile.permitted_claims_de),
        "forbidden_claims_de": list(profile.forbidden_claims_de),
        "residual_risks_de": list(profile.residual_risks_de),
        "subprocessor_jurisdictions": list(profile.subprocessor_jurisdictions),
    }
