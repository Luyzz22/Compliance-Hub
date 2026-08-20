"""Fixed-input Azure OpenAI brief for the synthetic, read-only demo workspace."""

from __future__ import annotations

import os

from sqlalchemy.orm import Session

from app.demo_models import (
    DemoAzureBriefContent,
    DemoAzureBriefResponse,
    DemoAzureBriefScenario,
)
from app.llm.client_wrapped import guardrailed_route_and_call_sync
from app.llm.context import LlmCallContext
from app.llm_models import LLMDataClass, LLMProvider, LLMTaskType
from app.repositories.tenant_registry import TenantRegistryRepository
from app.services import llm_client
from app.services.llm_json_utils import extract_json_object
from app.services.llm_usage_policy import current_llm_usage_policy

_SCENARIO_FACTS: dict[DemoAzureBriefScenario, str] = {
    DemoAzureBriefScenario.governance_release_gate: (
        "Ein synthetisches industrielles KI-System hat einen benannten Owner, eine offene "
        "DSFA-Prüfung, zwei ungeprüfte Evidence-Referenzen und noch keine Vier-Augen-Freigabe."
    ),
    DemoAzureBriefScenario.supplier_risk: (
        "Ein synthetischer Modelllieferant ist im Register erfasst. Das Ausstiegsverfahren, "
        "die Unterauftragnehmerprüfung und der Nachweis der Modelländerungskontrolle sind offen."
    ),
    DemoAzureBriefScenario.incident_readiness: (
        "Ein synthetischer KI-Betriebsfall besitzt ein Incident-Runbook. Eskalationsrollen, "
        "Beweissicherung und der dokumentierte Wiederanlauf wurden noch nicht gemeinsam geprobt."
    ),
}


def _enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def verify_demo_azure_runtime_configuration() -> None:
    """Reject an enabled demo inference path unless all safety gates are explicit."""
    if not _enabled("COMPLIANCEHUB_DEMO_AZURE_INFERENCE_ENABLED"):
        return

    required_flags = (
        "COMPLIANCEHUB_DEMO_SYNTHETIC_ONLY_ATTESTED",
        "COMPLIANCEHUB_FEATURE_DEMO_MODE",
        "COMPLIANCEHUB_DEMO_BLOCK_ALL_MUTATIONS",
        "COMPLIANCEHUB_FEATURE_LLM_ENABLED",
        "COMPLIANCEHUB_FEATURE_LLM_CHAT_ASSISTANT",
        "COMPLIANCEHUB_LLM_PREFER_AZURE",
        "COMPLIANCEHUB_LLM_ASSUME_AZURE_EU",
    )
    missing_flags = [name for name in required_flags if not _enabled(name)]
    if missing_flags:
        raise llm_client.LLMConfigurationError(
            "Demo Azure inference requires enabled safety flags: " + ", ".join(missing_flags),
        )
    if os.getenv("COMPLIANCEHUB_SOVEREIGNTY_MODE", "").strip() != "standard_dach":
        raise llm_client.LLMConfigurationError(
            "Demo Azure inference requires COMPLIANCEHUB_SOVEREIGNTY_MODE=standard_dach",
        )
    if os.getenv("COMPLIANCEHUB_LLM_PII_MODE", "block").strip() != "block":
        raise llm_client.LLMConfigurationError(
            "Demo Azure inference requires COMPLIANCEHUB_LLM_PII_MODE=block",
        )
    if os.getenv("AZURE_OPENAI_AUTH", "").strip() != "client_certificate":
        raise llm_client.LLMConfigurationError(
            "Demo Azure inference requires certificate-based Azure authentication",
        )
    if os.getenv("AZURE_OPENAI_API_KEY", "").strip():
        raise llm_client.LLMConfigurationError("Azure API keys are forbidden for the demo path")
    if not llm_client.is_provider_configured(LLMProvider.AZURE_OPENAI):
        raise llm_client.LLMConfigurationError(
            "Demo Azure inference requires a complete Azure OpenAI configuration",
        )

    usage = current_llm_usage_policy()
    max_output = llm_client.effective_max_output_tokens()
    if not 1 <= usage.daily_call_limit <= 100:
        raise llm_client.LLMConfigurationError(
            "Demo Azure inference requires a daily call limit between 1 and 100",
        )
    if not 1 <= usage.daily_token_limit <= 250_000:
        raise llm_client.LLMConfigurationError(
            "Demo Azure inference requires a daily token limit between 1 and 250000",
        )
    if usage.max_prompt_characters > 12_000 or max_output > 1024:
        raise llm_client.LLMConfigurationError(
            "Demo Azure inference prompt/output limits exceed the approved demo ceiling",
        )


def generate_demo_azure_brief(
    session: Session,
    *,
    tenant_id: str,
    scenario: DemoAzureBriefScenario,
) -> DemoAzureBriefResponse:
    """Run one fixed synthetic scenario through the approved Azure-only provider path."""
    if not _enabled("COMPLIANCEHUB_DEMO_AZURE_INFERENCE_ENABLED"):
        raise PermissionError("Azure demo inference is disabled")
    verify_demo_azure_runtime_configuration()
    tenant = TenantRegistryRepository(session).get_by_id(tenant_id)
    if tenant is None or not tenant.is_demo or tenant.demo_playground:
        raise PermissionError("Azure demo brief is available only in a read-only demo tenant")

    prompt = (
        "Erstelle aus dem folgenden ausschließlich synthetischen Governance-Szenario ein "
        "knappes deutschsprachiges Executive Briefing. Keine Rechtsberatung, keine automatische "
        "Risikoklassifikation und keine Freigabeentscheidung. Antworte nur als JSON mit den "
        "Schlüsseln title, executive_summary, recommended_actions (genau drei Einträge) und "
        "human_review_note. Szenario: "
        f"{_SCENARIO_FACTS[scenario]}"
    )
    response = guardrailed_route_and_call_sync(
        session,
        LLMTaskType.CHAT_ASSISTANT,
        prompt,
        tenant_id,
        context=LlmCallContext(
            tenant_id=tenant_id,
            action_name="demo.azure_governance_brief",
            data_class=LLMDataClass.PUBLIC,
        ),
        response_format="json_object",
        required_provider=LLMProvider.AZURE_OPENAI,
    )
    content = DemoAzureBriefContent.model_validate(extract_json_object(response.text))
    return DemoAzureBriefResponse(
        **content.model_dump(),
        scenario=scenario,
        provider="azure_openai",
        model_id=response.model_id,
        input_tokens_est=response.input_tokens_est,
        output_tokens_est=response.output_tokens_est,
    )
