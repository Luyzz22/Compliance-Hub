# Wave 8 — Advisor GA Readiness & Channel Abstraction

## Purpose

Wave 8 hardens the advisor stack for **GA with enterprise customers** (industrial mid-market, Steuerberater/WP-Kanzleien) and introduces a channel abstraction that enables future SAP and DATEV integrations without changing core advisor logic.

---

## 1. Advisor SLA & Error Model

### SLA Targets

| Metric | Target |
|--------|--------|
| End-to-end latency (p95) | ≤ 30 seconds |
| Error rate (sustained) | < 5% |
| Escalation rate (sustained) | < 40% |

### Error Categories

All advisor errors use a standardised shape (`AdvisorError`):

| Category | German message | `needs_manual_followup` | `retry_allowed` |
|----------|---------------|------------------------|-----------------|
| `rag_failure` | Quellensuche fehlgeschlagen | yes | yes |
| `llm_failure` | Antwortgenerierung nicht verfügbar | yes | no |
| `agent_failure` | Interner Verarbeitungsfehler | yes | yes |
| `timeout` | Zeitlimit überschritten | yes | yes |
| `policy_refusal` | Richtlinie abgelehnt | yes | no |
| `internal` | Unerwarteter Fehler | yes | no |

### Timeout Enforcement

The service layer (`app/advisor/service.py`) wraps agent execution in a thread pool with a configurable timeout (default: 30s). On timeout, a structured `AdvisorError(category="timeout")` is returned — the client never sees an unhandled exception.

### Fallback Behaviour

On any technical failure:
1. A structured `AdvisorError` with German + English messages is returned
2. `needs_manual_followup = true` is set
3. The error is logged as an `advisor_agent` event with `decision: "error"` for metrics
4. `trace_id` is propagated for debugging

---

## 2. Channel Abstraction

### Design

```
AdvisorRequest (query, tenant_id, channel, channel_metadata, request_id, trace_id)
     │
     ▼
  run_advisor()  ←  app/advisor/service.py (single entry point)
     │
     ├── idempotency check (request_id)
     ├── agent execution (with timeout)
     ├── channel-aware formatting
     ├── structured output derivation (tags, next_steps, ref_ids)
     └── metrics logging (channel, latency, errors)
     │
     ▼
  AdvisorStructuredResponse
```

### Channels

| Channel | `AdvisorChannel` value | Disclaimer | Max length | Use case |
|---------|----------------------|------------|-----------|----------|
| Web UI | `web` | Full | unlimited | Existing ComplianceHub web app |
| SAP | `sap` | Stripped | 4000 chars | SAP integration adapter |
| DATEV | `datev` | Stripped | 3000 chars | DATEV Kanzlei integration |
| API Partner | `api_partner` | Full | 8000 chars | Third-party API consumers |

### Channel Metadata

Requests can carry channel-specific context via `ChannelMetadata`:

```python
ChannelMetadata(
    sap_document_id="DOC-42",       # SAP document reference
    datev_client_number="KD-999",   # DATEV Mandantennummer
    partner_reference="REF-1",      # Generic partner reference
    extra={...},                    # Extensible
)
```

These are propagated to `ref_ids` in the response for linking back into ERP/DATEV entities.

### Adding a New Channel

1. Add the channel to `AdvisorChannel` enum in `app/advisor/channels.py`
2. Configure max answer length and disclaimer behaviour
3. Optionally add fields to `ChannelMetadata`
4. No changes to core agent logic required

---

## 3. Structured Output

Every `AdvisorStructuredResponse` includes:

| Field | Type | Purpose |
|-------|------|---------|
| `answer` | string | Human-readable answer (backwards compatible) |
| `tags` | list[str] | Topic tags derived from query + answer (`eu_ai_act`, `nis2`, `high_risk`, `risk_management`, ...) |
| `suggested_next_steps` | list[str] | Actionable German-language suggestions |
| `ref_ids` | dict[str, str] | Channel-specific entity references for ERP linking |
| `meta` | object | Channel, request_id, trace_id, latency, is_cached |
| `error` | object\|null | Structured error if failed |

### Tag Derivation

Tags are derived via regex patterns matching against query + answer text. This keeps tagging deterministic and auditable (no LLM involved).

### Next Steps

Generated based on escalation status, confidence level, and tags. Escalated queries always suggest contacting a compliance advisor first.

---

## 4. Idempotency

### Problem

SAP and DATEV systems may retry requests on network errors. Without idempotency, retries cause:
- Duplicate metric counts
- Duplicate evidence events
- Wasted compute

### Solution

`app/advisor/idempotency.py` provides an in-process LRU cache:

- Clients supply a `request_id` with each request
- If the same `request_id` is received within the TTL window (5 min), the cached response is returned with `meta.is_cached = true`
- Duplicates are logged with `decision: "duplicate"` in metrics (not double-counted as queries)
- Cache: max 500 entries, in-process (sufficient for beta)

### Without `request_id`

Requests without `request_id` are always executed fresh (backwards compatible).

---

## 5. Metrics & Monitoring Extensions

### New Metrics

| Metric | Source |
|--------|--------|
| Channel distribution | `advisor_agent` events with `extra.channel` |
| Error rate | `decision: "error"` events / total decisions |
| Duplicate rate | `decision: "duplicate"` events |
| Latency p50 / p95 | `extra.latency_ms` from agent events |

### Alert Thresholds (for ops documentation)

| Alert | Condition | Action |
|-------|-----------|--------|
| High error rate | error_rate > 5% sustained over 1h | Investigate RAG/LLM health |
| High escalation rate | escalation_rate > 40% sustained over 1h | Review corpus coverage |
| Latency breach | p95 > 30s sustained over 15min | Check LLM provider latency |
| Channel anomaly | Single channel error_rate > 20% | Check channel-specific integration |

These alerts should be configured in the monitoring system (e.g. Grafana/PagerDuty) once production telemetry is available.

---

## 6. Files

| File | Change |
|------|--------|
| `app/advisor/channels.py` | New: Channel enum, metadata, formatting config |
| `app/advisor/errors.py` | New: Error model, categories, builder |
| `app/advisor/idempotency.py` | New: Request-level idempotency cache |
| `app/advisor/response_models.py` | New: Structured response with tags, next_steps, ref_ids |
| `app/advisor/formatting.py` | New: Channel-aware formatting, tag derivation, next steps |
| `app/advisor/service.py` | New: GA-ready service layer (timeout, error handling, channels) |
| `app/advisor/templates.py` | Extended: Added compact disclaimer variant for ERP channels |
| `app/advisor/metrics.py` | Extended: Channel distribution, error rate, latency percentiles |
| `tests/test_advisor_ga.py` | New: 23 tests for errors, channels, idempotency, structured output, metrics |
| `docs/architecture/wave8-advisor-ga-and-channels.md` | This document |

---

## 7. Backwards Compatibility

All changes are additive:

- Existing web clients continue to work unchanged (default `channel="web"`)
- The core `AdvisorComplianceAgent` is not modified — the service layer wraps it
- Existing API endpoints are not changed; `run_advisor()` is a new entry point
- Metrics extensions only add new fields to `AdvisorMetricsResponse`
- `request_id` is optional — omitting it preserves existing behaviour
