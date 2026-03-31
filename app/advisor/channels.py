"""Advisor channel abstraction for multi-channel delivery.

Channels let the same advisor core serve web, SAP, DATEV, and API partner
integrations without changing business logic. Channel-specific behaviour
(formatting, disclaimers, field selection) is encapsulated here.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AdvisorChannel(StrEnum):
    web = "web"
    sap = "sap"
    datev = "datev"
    api_partner = "api_partner"


class ChannelMetadata(BaseModel):
    """Optional channel-specific context attached to a request."""

    sap_document_id: str | None = None
    datev_client_number: str | None = None
    partner_reference: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


DEFAULT_CHANNEL = AdvisorChannel.web


def max_answer_length(channel: AdvisorChannel) -> int | None:
    """Channel-specific max answer length (characters). None = unlimited."""
    _limits: dict[AdvisorChannel, int | None] = {
        AdvisorChannel.web: None,
        AdvisorChannel.sap: 4000,
        AdvisorChannel.datev: 3000,
        AdvisorChannel.api_partner: 8000,
    }
    return _limits.get(channel)


def include_disclaimer(channel: AdvisorChannel) -> bool:
    """Whether the channel should include the legal disclaimer in answers."""
    return channel in (AdvisorChannel.web, AdvisorChannel.api_partner)
