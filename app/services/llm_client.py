"""HTTP-based LLM clients (httpx); keys and base URLs from environment."""

from __future__ import annotations

import json
import os
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
        LLMProvider.GEMINI: "gemini-2.0-flash",
        LLMProvider.LLAMA: "llama-3.1-8b-instruct",
    }
    env_keys = {
        LLMProvider.CLAUDE: "COMPLIANCEHUB_CLAUDE_MODEL",
        LLMProvider.OPENAI: "COMPLIANCEHUB_OPENAI_MODEL",
        LLMProvider.GEMINI: "COMPLIANCEHUB_GEMINI_MODEL",
        LLMProvider.LLAMA: "COMPLIANCEHUB_LLAMA_MODEL",
    }
    key = env_keys[provider]
    return _env(key) or defaults[provider]


def embedding_model_id(provider: LLMProvider) -> str:
    if provider == LLMProvider.OPENAI:
        return _env("COMPLIANCEHUB_OPENAI_EMBEDDING_MODEL") or "text-embedding-3-small"
    if provider == LLMProvider.LLAMA:
        return _env("COMPLIANCEHUB_LLAMA_EMBEDDING_MODEL") or chat_model_id(LLMProvider.LLAMA)
    return chat_model_id(provider)


def is_provider_configured(provider: LLMProvider) -> bool:
    if provider == LLMProvider.CLAUDE:
        return bool(_env("CLAUDE_API_KEY") or _env("ANTHROPIC_API_KEY"))
    if provider == LLMProvider.OPENAI:
        return bool(_env("OPENAI_API_KEY"))
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
        raise LLMProviderHTTPError(f"Anthropic HTTP {r.status_code}: {r.text[:500]}")
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
        raise LLMProviderHTTPError(f"OpenAI HTTP {r.status_code}: {r.text[:500]}")
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
        raise LLMProviderHTTPError(f"Gemini HTTP {r.status_code}: {r.text[:500]}")
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
        raise LLMProviderHTTPError(f"Llama HTTP {r.status_code}: {r.text[:500]}")
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
            raise LLMProviderHTTPError(f"Llama embeddings HTTP {r.status_code}: {r.text[:500]}")
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
            raise LLMProviderHTTPError(f"OpenAI embeddings HTTP {r.status_code}: {r.text[:500]}")
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
    raise LLMConfigurationError(f"Embeddings not implemented for provider: {provider}")
