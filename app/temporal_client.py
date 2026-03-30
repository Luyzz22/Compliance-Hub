"""Shared Temporal client (lazy connect) for FastAPI and tooling."""

from __future__ import annotations

import asyncio
import logging

from temporalio.client import Client

from app.workflows.config import (
    temporal_address,
    temporal_api_key,
    temporal_namespace,
    temporal_tls_enabled,
)

logger = logging.getLogger(__name__)

_client: Client | None = None
_lock = asyncio.Lock()


async def get_temporal_client() -> Client:
    global _client
    async with _lock:
        if _client is None:
            connect_kwargs: dict = {"namespace": temporal_namespace()}
            key = temporal_api_key()
            if key:
                connect_kwargs["api_key"] = key
                connect_kwargs["tls"] = True
            elif temporal_tls_enabled():
                connect_kwargs["tls"] = True
            logger.info(
                "temporal_client_connecting address=%s namespace=%s tls=%s",
                temporal_address(),
                temporal_namespace(),
                connect_kwargs.get("tls", False),
            )
            _client = await Client.connect(temporal_address(), **connect_kwargs)
    return _client


def reset_temporal_client_for_tests() -> None:
    """Test hook: clear cached client after monkeypatching env."""
    global _client
    _client = None
