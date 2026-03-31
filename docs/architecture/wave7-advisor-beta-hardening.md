# Wave 7 — Advisor Beta Hardening

## Purpose

Wave 7 prepares the advisor stack for **beta with real users** by adding internal quality and safety monitoring (metrics), tightening agent policies around sensitive topics, and standardising answer templates for legal review.

No raw prompts or PII flow into metrics or logs — only aggregated counts, category labels, and hashed identifiers.

---

## 1. Advisor Metrics

### What is tracked

| Metric | Granularity | Source event |
|--------|-------------|--------------|
| Total advisor queries | per day, per tenant | `rag_query` |
| Retrieval mode distribution (BM25 vs. hybrid) | per day, per tenant | `rag_query.retrieval_mode` |
| Confidence buckets (high / medium / low) | per day, per tenant | `rag_query.confidence_level` |
| Agent decisions (answered vs. escalated) | per day, per tenant | `advisor_agent.decision` |
| Escalation rate | aggregate | derived from agent decisions |

### Why these metrics

- **Volume**: detect sudden spikes or drops that may indicate misconfiguration or abuse.
- **Retrieval mode**: monitor adoption of hybrid retrieval and detect fallback-to-BM25 in environments where `sentence-transformers` is unavailable.
- **Confidence distribution**: track model and corpus quality over time — a shift toward low-confidence answers signals corpus gaps or drift.
- **Escalation rate**: core safety indicator — a rising rate may indicate new query patterns that the agent cannot handle safely.

### Architecture

```
Evidence Store (in-memory ring buffer)
  ├── rag_query events
  └── advisor_agent events
        │
        ▼
  app/advisor/metrics.py
  └── aggregate_advisor_metrics()
        │
        ▼
  GET /api/internal/advisor/metrics
  (feature-flagged + OPA-guarded)
        │
        ▼
  Internal Dashboard (Next.js)
  /internal/advisor-metrics
```

- `app/advisor/metrics.py`: Reads from the existing evidence store ring buffer. Groups events by day and tenant. Returns `AdvisorMetricsResponse` with aggregate totals and daily breakdowns.
- **No additional DB table**: aggregation runs over the in-memory store on each request. Sufficient for beta volumes (<2000 events in the ring buffer).
- **Feature flag**: `advisor_metrics_internal` (env `COMPLIANCEHUB_FEATURE_ADVISOR_METRICS_INTERNAL`, default `false`).
- **OPA guard**: `view_advisor_metrics` action, `platform_admin` role by default.

---

## 2. Agent Policy Rules

### Sensitive topics detection

Module: `app/advisor/sensitive_topics.py`

A rule-based classifier checks queries against:

1. **Prohibited keywords** (e.g. `social scoring`, `Massenüberwachung`, `predictive policing`) → immediate refusal, no RAG call.
2. **Sensitive keywords** (e.g. `biometrisch`, `Emotionserkennung`, `Arbeitnehmerüberwachung`, `Deepfake`) → flagged for policy gate.
3. **Sensitive patterns** (regex, e.g. `biometrisch\w*\s+kategori`) → fallback for compound terms.

### Policy decisions

| Condition | Action | Template | Policy rule ID |
|-----------|--------|----------|----------------|
| Prohibited topic | Immediate refusal (no RAG) | `REFUSAL_PROHIBITED_TOPIC` | `prohibited_topic` |
| Sensitive + low/medium confidence | Escalate to human | `REFUSAL_SENSITIVE_LOW_CONFIDENCE` | `sensitive_{rule_id}` |
| Sensitive + high confidence | Allow synthesis | `ANSWER_NORMAL` (with disclaimer) | — |
| Out-of-scope intent | Refusal | `REFUSAL_OUT_OF_SCOPE` | `out_of_scope` |
| Low confidence (non-sensitive) | Escalate to human | `ESCALATION_HUMAN_REVIEW` | `low_confidence` |
| Tenant guidance missing | Escalate | `ESCALATION_HUMAN_REVIEW` | `low_confidence` |

### Agent graph (updated)

```
START → classify_intent
            │
    ┌───────┼───────┐
    ▼       ▼       ▼
 check_   escalate  END (out_of_scope w/ template)
 sensitive
    │
    ├─ prohibited → escalate (w/ REFUSAL_PROHIBITED_TOPIC)
    │
    ▼
 run_rag_query
    │
    ▼
 check_confidence
    │
    ├─ sensitive + low/medium → escalate (w/ REFUSAL_SENSITIVE)
    ├─ tenant guidance missing → escalate
    ├─ low confidence → escalate
    │
    ▼
 synthesize_answer (w/ ANSWER_NORMAL + disclaimer)
    │
    ▼
   END
```

### Audit logging

Every agent decision now logs:

- `policy_rule_id`: which rule triggered the decision
- `sensitive_matched_term`: the keyword/pattern that matched (if sensitive)
- `sensitive_rule_id`: `prohibited_topic`, `sensitive_keyword`, or `sensitive_pattern`

These fields appear in the `agent_trace` (per-request) and in the evidence store `advisor_agent` events (persistent).

Successful auto-answers now also produce an `advisor_agent` event with `decision: "answered"` to enable accurate answered-vs-escalated metrics.

---

## 3. Answer Templates

Module: `app/advisor/templates.py`

All German-language templates are centralised for legal/compliance review:

| Template | Usage |
|----------|-------|
| `ANSWER_NORMAL` | Normal answers, appends `DISCLAIMER_KEINE_RECHTSBERATUNG` |
| `ESCALATION_HUMAN_REVIEW` | General human escalation with reason |
| `REFUSAL_PROHIBITED_TOPIC` | Prohibited AI Act topics (static text) |
| `REFUSAL_OUT_OF_SCOPE` | Non-compliance queries |
| `REFUSAL_SENSITIVE_LOW_CONFIDENCE` | Sensitive topics with insufficient confidence |
| `DISCLAIMER_KEINE_RECHTSBERATUNG` | Standalone disclaimer constant |

Helper functions `format_normal_answer()`, `format_escalation()`, and `format_sensitive_refusal()` handle string interpolation.

---

## 4. Regulatory Alignment

### EU AI Act (Regulation 2024/1689)

- **Art. 9 (Risk Management)**: Metrics on confidence distribution and escalation rate support ongoing risk monitoring of the AI advisor system.
- **Art. 5 (Prohibited practices)**: `prohibited_topic` detection enforces immediate refusal for social scoring, mass surveillance, and predictive policing queries.
- **Art. 50 (Transparency)**: Disclaimers ensure users understand the AI advisor does not provide legal advice.
- **Annex III / Art. 6**: Sensitive topic detection covers high-risk categories (biometrics, emotion recognition, workforce surveillance).

### ISO 42001 (AI Management System)

- **A.7.2 (Risk identification)**: Metrics serve as quantitative input for periodic risk reviews.
- **A.7.5 (Monitoring and measurement)**: Daily metrics by tenant enable continuous monitoring of AI system performance.
- **A.8.4 (Documentation)**: Agent trace with `policy_rule_id` provides auditable decision records.

### NIS2

- **Art. 21 (Risk-management measures)**: Escalation rate monitoring detects anomalous query patterns that may indicate security-relevant compliance gaps.

---

## 5. Files Changed

| File | Change |
|------|--------|
| `app/advisor/__init__.py` | New package |
| `app/advisor/metrics.py` | Metrics aggregation module |
| `app/advisor/sensitive_topics.py` | Sensitive topic classifier |
| `app/advisor/templates.py` | German answer templates |
| `app/services/agents/advisor_compliance_agent.py` | Integrated sensitive topic check, templates, `answered` event logging |
| `app/feature_flags.py` | Added `advisor_metrics_internal` flag |
| `app/main.py` | Added `GET /api/internal/advisor/metrics` endpoint |
| `frontend/src/lib/config.ts` | Added `featureAdvisorMetricsInternal()` |
| `frontend/src/lib/api.ts` | Added `fetchAdvisorMetrics()` |
| `frontend/src/app/internal/advisor-metrics/page.tsx` | Internal metrics dashboard |
| `tests/test_advisor_metrics.py` | Metrics aggregation tests |
| `tests/test_advisor_policies.py` | Policy and sensitive topic tests |
| `docs/architecture/wave7-advisor-beta-hardening.md` | This document |
