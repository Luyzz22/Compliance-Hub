# Compliance Mapping – DSGVO, EU AI Act, GoBD, E‑Rechnung

## DSGVO

- VVT‑Pflicht (Art. 30): Abgebildet über `create_or_update_ropa_entry`‑Aktion aus der Engine.
- Drittlandtransfers (Kapitel V): `trigger_transfer_impact_assessment` bei Nicht‑DACH‑Lieferanten.
- Privacy by Default: Standardmäßig `contains_personal_data=True` mit Human‑Approval‑Gate.

## EU AI Act (Auszug)

- Human Oversight: `require_human_approval`‑Aktion als explizites Control.
- Transparency: Audit‑Events über `/api/v1/platform/audit` exportierbar.
- Risk‑Based Approach: Severity‑Enum (`low`, `medium`, `high`, `critical`) als Normalisierungsschicht.

## GoBD

- Unveränderbarkeit: Hash‑Erzeugung in `build_audit_hash`.
- Nachvollziehbarkeit: Aktionen pro Dokument als Audit‑Trail.
- Verfahrensdokumentation: Grundlage für process‑dokument exports aus der Engine.

## E‑Rechnung

- EN‑16931: Feld `xml_valid_en16931` als Validierungsflag.
- Formate: `EInvoiceFormat`‑Enum (XRechnung, ZUGFeRD, unknown).
- B2B‑Pflicht: Nicht‑konforme Formate erzeugen `request_einvoice_replacement`.

