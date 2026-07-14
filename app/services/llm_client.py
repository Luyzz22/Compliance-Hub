"""HTTP-based LLM clients (httpx); keys and base URLs from environment."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

import httpx

from app.llm_models import LLMProvider, LLMResponse


class LLMConfigurationError(RuntimeError):
    """Missing API key, base URL, or local endpoint."""


class LLMProviderHTTPError(RuntimeError):
    """Upstream LLM API returned an error response."""


def _env(name: str, default: str | None = None) -> str | None:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip()


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def chat_model_id(provider: LLMProvider) -> str:
    defaults = {
        LLMProvider.CLAUDE: "claude-sonnet-4-20250514",
        LLMProvider.OPENAI: "gpt-4o",
        LLMProvider.AZURE_OPENAI: "",
        LLMProvider.GEMINI: "gemini-2.0-flash",
        LLMProvider.LLAMA: "llama-3.1-8b-instruct",
    }
    env_keys = {
        LLMProvider.CLAUDE: "COMPLIANCEHUB_CLAUDE_MODEL",
        LLMProvider.OPENAI: "COMPLIANCEHUB_OPENAI_MODEL",
        LLMProvider.AZURE_OPENAI: "AZURE_OPENAI_DEPLOYMENT",
        LLMProvider.GEMINI: "COMPLIANCEHUB_GEMINI_MODEL",
        LLMProvider.LLAMA: "COMPLIANCEHUB_LLAMA_MODEL",
    }
    key = env_keys[provider]
    return _env(key) or defaults[provider]


def embedding_model_id(provider: LLMProvider) -> str:
    if provider == LLMProvider.OPENAI:
        return _env("COMPLIANCEHUB_OPENAI_EMBEDDING_MODEL") or "text-embedding-3-small"
    if provider == LLMProvider.AZURE_OPENAI:
        return _env("AZURE_OPENAI_EMBEDDING_DEPLOYMENT") or ""
    if provider == LLMProvider.LLAMA:
        return _env("COMPLIANCEHUB_LLAMA_EMBEDDING_MODEL") or chat_model_id(LLMProvider.LLAMA)
    return chat_model_id(provider)


def is_provider_configured(provider: LLMProvider) -> bool:
    if provider == LLMProvider.CLAUDE:
        return bool(_env("CLAUDE_API_KEY") or _env("ANTHROPIC_API_KEY"))
    if provider == LLMProvider.OPENAI:
        return bool(_env("OPENAI_API_KEY"))
    if provider == LLMProvider.AZURE_OPENAI:
        if not _env("AZURE_OPENAI_ENDPOINT") or not _env("AZURE_OPENAI_DEPLOYMENT"):
            return False
        auth_mode = (_env("AZURE_OPENAI_AUTH", "managed_identity") or "").lower()
        return auth_mode == "managed_identity" or bool(_env("AZURE_OPENAI_API_KEY"))
    if provider == LLMProvider.GEMINI:
        return bool(_env("GEMINI_API_KEY") or _env("GOOGLE_API_KEY"))
    if provider == LLMProvider.LLAMA:
        return bool(_env("LLAMA_BASE_URL"))
    return False


def _anthropic_key() -> str:
    k = _env("CLAUDE_API_KEY") or _env("ANTHROPIC_API_KEY")
    if not k:
        raise LLMConfigurationError("CLAUDE_API_KEY or ANTHROPIC_API_KEY is not set")
    return k


def _call_claude(model_id: str, prompt: str, **kwargs: Any) -> LLMResponse:
    max_tokens = int(kwargs.get("max_tokens") or 1024)
    base = _env("ANTHROPIC_API_URL", "https://api.anthropic.com")
    url = f"{base.rstrip('/')}/v1/messages"
    payload = {
        "model": model_id,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "x-api-key": _anthropic_key(),
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    with httpx.Client(timeout=120.0) as client:
        r = client.post(url, json=payload, headers=headers)
    if r.status_code >= 400:
        _raise_provider_http_error("Anthropic", r)
    data = r.json()
    parts = data.get("content") or []
    texts: list[str] = []
    for block in parts:
        if isinstance(block, dict) and block.get("type") == "text":
            texts.append(str(block.get("text", "")))
    text = "\n".join(texts).strip()
    in_tok = int(data.get("usage", {}).get("input_tokens") or _estimate_tokens(prompt))
    out_tok = int(data.get("usage", {}).get("output_tokens") or _estimate_tokens(text))
    return LLMResponse(
        text=text,
        provider=LLMProvider.CLAUDE,
        model_id=model_id,
        input_tokens_est=in_tok,
        output_tokens_est=out_tok,
    )


def _openai_key() -> str:
    k = _env("OPENAI_API_KEY")
    if not k:
        raise LLMConfigurationError("OPENAI_API_KEY is not set")
    return k


def _raise_provider_http_error(provider: str, response: httpx.Response) -> None:
    """Raise a sanitized error without persisting an upstream response body."""
    request_id = (
        response.headers.get("x-request-id")
        or response.headers.get("apim-request-id")
        or response.headers.get("request-id")
    )
    error_code: str | None = None
    try:
        payload = response.json()
        if isinstance(payload, dict):
            raw_error = payload.get("error")
            if isinstance(raw_error, dict) and raw_error.get("code") is not None:
                error_code = str(raw_error["code"])[:80]
    except (ValueError, TypeError):
        pass
    detail = f"{provider} HTTP {response.status_code}"
    if error_code:
        detail += f" code={error_code}"
    if request_id:
        detail += f" request_id={request_id[:128]}"
    raise LLMProviderHTTPError(detail)


def _call_openai_chat(model_id: str, prompt: str, **kwargs: Any) -> LLMResponse:
    base = _env("OPENAI_BASE_URL", "https://api.openai.com/v1")
    url = f"{base.rstrip('/')}/chat/completions"
    payload: dict[str, Any] = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
    }
    if kwargs.get("response_format") == "json_object":
        payload["response_format"] = {"type": "json_object"}
    headers = {"authorization": f"Bearer {_openai_key()}", "content-type": "application/json"}
    with httpx.Client(timeout=120.0) as client:
        r = client.post(url, json=payload, headers=headers)
    if r.status_code >= 400:
        _raise_provider_http_error("OpenAI", r)
    data = r.json()
    choice0 = (data.get("choices") or [{}])[0]
    msg = choice0.get("message") or {}
    text = str(msg.get("content") or "").strip()
    usage = data.get("usage") or {}
    in_tok = int(usage.get("prompt_tokens") or _estimate_tokens(prompt))
    out_tok = int(usage.get("completion_tokens") or _estimate_tokens(text))
    return LLMResponse(
        text=text,
        provider=LLMProvider.OPENAI,
        model_id=model_id,
        input_tokens_est=in_tok,
        output_tokens_est=out_tok,
    )


def _azure_openai_base() -> str:
    endpoint = _env("AZURE_OPENAI_ENDPOINT")
    if not endpoint:
        raise LLMConfigurationError("AZURE_OPENAI_ENDPOINT is not set")
    base = endpoint.rstrip("/")
    if not base.endswith("/openai/v1"):
        base = f"{base}/openai/v1"
    if not base.startswith("https://") and not _env("COMPLIANCEHUB_ALLOW_INSECURE_LLM_ENDPOINTS"):
        raise LLMConfigurationError("AZURE_OPENAI_ENDPOINT must use HTTPS")
    return base


@lru_cache(maxsize=1)
def _azure_credential() -> Any:
    try:
        from azure.identity import DefaultAzureCredential
    except ImportError as exc:  # pragma: no cover - dependency is part of production install
        raise LLMConfigurationError("azure-identity is required for managed identity") from exc
    return DefaultAzureCredential()


def _azure_openai_headers() -> dict[str, str]:
    auth_mode = (_env("AZURE_OPENAI_AUTH", "managed_identity") or "").lower()
    headers = {"content-type": "application/json"}
    if auth_mode == "api_key":
        key = _env("AZURE_OPENAI_API_KEY")
        if not key:
            raise LLMConfigurationError("AZURE_OPENAI_API_KEY is not set")
        headers["api-key"] = key
        return headers
    if auth_mode != "managed_identity":
        raise LLMConfigurationError("AZURE_OPENAI_AUTH must be managed_identity or api_key")
    token = _azure_credential().get_token("https://cognitiveservices.azure.com/.default")
    headers["authorization"] = f"Bearer {token.token}"
    return headers


def _call_azure_openai_chat(model_id: str, prompt: str, **kwargs: Any) -> LLMResponse:
    if not model_id:
        raise LLMConfigurationError("AZURE_OPENAI_DEPLOYMENT is not set")
    payload: dict[str, Any] = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
    }
    if kwargs.get("response_format") == "json_object":
        payload["response_format"] = {"type": "json_object"}
    with httpx.Client(timeout=120.0, follow_redirects=False) as client:
        response = client.post(
            f"{_azure_openai_base()}/chat/completions",
            json=payload,
            headers=_azure_openai_headers(),
        )
    if response.status_code >= 400:
        _raise_provider_http_error("Azure OpenAI", response)
    data = response.json()
    choice0 = (data.get("choices") or [{}])[0]
    message = choice0.get("message") or {}
    text = str(message.get("content") or "").strip()
    usage = data.get("usage") or {}
    return LLMResponse(
        text=text,
        provider=LLMProvider.AZURE_OPENAI,
        model_id=model_id,
        input_tokens_est=int(usage.get("prompt_tokens") or _estimate_tokens(prompt)),
        output_tokens_est=int(usage.get("completion_tokens") or _estimate_tokens(text)),
    )


def _gemini_key() -> str:
    k = _env("GEMINI_API_KEY") or _env("GOOGLE_API_KEY")
    if not k:
        raise LLMConfigurationError("GEMINI_API_KEY or GOOGLE_API_KEY is not set")
    return k


def _call_gemini(model_id: str, prompt: str, **kwargs: Any) -> LLMResponse:
    key = _gemini_key()
    base = _env("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta")
    url = f"{base.rstrip('/')}/models/{model_id}:generateContent"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    with httpx.Client(timeout=120.0) as client:
        r = client.post(url, params={"key": key}, json=payload)
    if r.status_code >= 400:
        _raise_provider_http_error("Gemini", r)
    data = r.json()
    candidates = data.get("candidates") or []
    text = ""
    if candidates:
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(str(p.get("text", "")) for p in parts if isinstance(p, dict)).strip()
    meta = data.get("usageMetadata") or {}
    in_tok = int(meta.get("promptTokenCount") or _estimate_tokens(prompt))
    out_tok = int(meta.get("candidatesTokenCount") or _estimate_tokens(text))
    return LLMResponse(
        text=text,
        provider=LLMProvider.GEMINI,
        model_id=model_id,
        input_tokens_est=in_tok,
        output_tokens_est=out_tok,
    )


def _llama_base() -> str:
    u = _env("LLAMA_BASE_URL")
    if not u:
        raise LLMConfigurationError("LLAMA_BASE_URL is not set")
    return u.rstrip("/")


def _call_llama_chat(model_id: str, prompt: str, **kwargs: Any) -> LLMResponse:
    url = f"{_llama_base()}/v1/chat/completions"
    headers: dict[str, str] = {"content-type": "application/json"}
    lk = _env("LLAMA_API_KEY")
    if lk:
        headers["authorization"] = f"Bearer {lk}"
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
    }
    with httpx.Client(timeout=120.0) as client:
        r = client.post(url, json=payload, headers=headers)
    if r.status_code >= 400:
        _raise_provider_http_error("Llama", r)
    data = r.json()
    choice0 = (data.get("choices") or [{}])[0]
    msg = choice0.get("message") or {}
    text = str(msg.get("content") or "").strip()
    usage = data.get("usage") or {}
    in_tok = int(usage.get("prompt_tokens") or _estimate_tokens(prompt))
    out_tok = int(usage.get("completion_tokens") or _estimate_tokens(text))
    return LLMResponse(
        text=text,
        provider=LLMProvider.LLAMA,
        model_id=model_id,
        input_tokens_est=in_tok,
        output_tokens_est=out_tok,
    )


def call_model(provider: LLMProvider, model_id: str, prompt: str, **kwargs: Any) -> LLMResponse:
    """
    Dispatch chat completion to the selected provider.

    Optional kwargs: max_tokens, response_format (OpenAI: json_object).
    """
    if provider == LLMProvider.CLAUDE:
        return _call_claude(model_id, prompt, **kwargs)
    if provider == LLMProvider.OPENAI:
        return _call_openai_chat(model_id, prompt, **kwargs)
    if provider == LLMProvider.AZURE_OPENAI:
        return _call_azure_openai_chat(model_id, prompt, **kwargs)
    if provider == LLMProvider.GEMINI:
        return _call_gemini(model_id, prompt, **kwargs)
    if provider == LLMProvider.LLAMA:
        return _call_llama_chat(model_id, prompt, **kwargs)
    raise LLMConfigurationError(f"Unsupported provider: {provider}")


def call_embedding(provider: LLMProvider, model_id: str, input_text: str) -> LLMResponse:
    """
    Embeddings for RAG-style tasks. Returns JSON array string in ``text`` (for downstream use).
    """
    if not input_text.strip():
        return LLMResponse(
            text="[]",
            provider=provider,
            model_id=model_id,
            input_tokens_est=0,
            output_tokens_est=0,
        )
    if provider == LLMProvider.LLAMA:
        url = f"{_llama_base()}/v1/embeddings"
        headers: dict[str, str] = {"content-type": "application/json"}
        lk = _env("LLAMA_API_KEY")
        if lk:
            headers["authorization"] = f"Bearer {lk}"
        payload = {"model": model_id, "input": input_text}
        with httpx.Client(timeout=120.0) as client:
            r = client.post(url, json=payload, headers=headers)
        if r.status_code >= 400:
            _raise_provider_http_error("Llama embeddings", r)
        data = r.json()
        vec = (data.get("data") or [{}])[0].get("embedding") or []
        text = json.dumps(vec)
        return LLMResponse(
            text=text,
            provider=LLMProvider.LLAMA,
            model_id=model_id,
            input_tokens_est=_estimate_tokens(input_text),
            output_tokens_est=len(vec),
        )
    if provider == LLMProvider.OPENAI:
        base = _env("OPENAI_BASE_URL", "https://api.openai.com/v1")
        url = f"{base.rstrip('/')}/embeddings"
        headers = {"authorization": f"Bearer {_openai_key()}", "content-type": "application/json"}
        payload = {"model": model_id, "input": input_text}
        with httpx.Client(timeout=120.0) as client:
            r = client.post(url, json=payload, headers=headers)
        if r.status_code >= 400:
            _raise_provider_http_error("OpenAI embeddings", r)
        data = r.json()
        vec = (data.get("data") or [{}])[0].get("embedding") or []
        text = json.dumps(vec)
        return LLMResponse(
            text=text,
            provider=LLMProvider.OPENAI,
            model_id=model_id,
            input_tokens_est=int((data.get("usage") or {}).get("prompt_tokens") or 0)
            or _estimate_tokens(input_text),
            output_tokens_est=len(vec),
        )
    if provider == LLMProvider.AZURE_OPENAI:
        if not model_id:
            raise LLMConfigurationError("AZURE_OPENAI_EMBEDDING_DEPLOYMENT is not set")
        payload = {"model": model_id, "input": input_text}
        with httpx.Client(timeout=120.0, follow_redirects=False) as client:
            response = client.post(
                f"{_azure_openai_base()}/embeddings",
                json=payload,
                headers=_azure_openai_headers(),
            )
        if response.status_code >= 400:
            _raise_provider_http_error("Azure OpenAI embeddings", response)
        data = response.json()
        vector = (data.get("data") or [{}])[0].get("embedding") or []
        return LLMResponse(
            text=json.dumps(vector),
            provider=LLMProvider.AZURE_OPENAI,
            model_id=model_id,
            input_tokens_est=int((data.get("usage") or {}).get("prompt_tokens") or 0)
            or _estimate_tokens(input_text),
            output_tokens_est=len(vector),
        )
    raise LLMConfigurationError(f"Embeddings not implemented for provider: {provider}")
