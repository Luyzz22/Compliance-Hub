# Wave 33 – Product ↔ GTM Bridge (Readiness-Overlay)

Ziel: **ohne Data Warehouse** sichtbar machen, wo GTM-Nachfrage (Segmente, Leads) und **Produkt-/Governance-Reife** auseinanderlaufen – für Founder-Entscheidungen (Delivery, Enablement, Piloten).

## 1. Mapping (manuelle Brücke)

Datei: `data/gtm-product-account-map.json` (oder `GTM_PRODUCT_ACCOUNT_MAP_PATH`, auf Vercel optional `/tmp/...`).

Struktur:

```json
{
  "entries": [
    {
      "tenant_id": "tenant-demo-001",
      "domain": "kunde.example",
      "label": "Beispiel GmbH",
      "pilot": true
    },
    {
      "tenant_id": "tenant-pilot-xyz",
      "account_key": "ac_v1_co_…",
      "label": "Hash-basiert wie in Lead-Inbox"
    }
  ]
}
```

**Zuordnung zu Leads**

1. Wenn `account_key` gesetzt ist und mit `lead_account_key` des Leads übereinstimmt → Treffer.
2. Sonst: normalisierte Domain aus `business_email` gegen `domain`.

Ohne Treffer gilt der Lead in der Matrix als **Kein Mandanten-Footprint (nur GTM)**.

## 2. Readiness-Klassen (Produktseite)

Implementierung: `frontend/src/lib/gtmAccountReadiness.ts` (anpassbare Regeln).

| Klasse | Bedeutung (kurz) |
|--------|------------------|
| `no_footprint` | Kein Mapping → nur GTM-Sicht |
| `early_pilot` | Mandant gemappt, aber unter Baseline-Schwelle oder API nicht lesbar |
| `baseline_governance` | Board-Report-Spur (Setup-Schritt 6) **oder** Inventar + KPI-Register (Schritte 3+4 / Systeme + KPIs) |
| `advanced_governance` | Schritt 6 **und** ≥2 KI-Systeme **und** ≥2 aktive Frameworks im Setup |

Die **Fortschrittsschritte 1–6** entsprechen der Backend-Logik in `app/services/tenant_ai_governance_setup.py` (u. a. Systeme, KPI-Werte, Board-Report).

## 3. Live-Signale (API)

Der Next.js-Server ruft pro **eindeutigem** `tenant_id` aus dem Mapping auf:

- `GET /api/v1/tenants/{tenant_id}/ai-governance-setup`
- `GET /api/v1/ai-systems`

Konfiguration: `COMPLIANCEHUB_API_BASE_URL` und `COMPLIANCEHUB_API_KEY` (Fallback: `NEXT_PUBLIC_*`). Ohne erreichbares Backend bleiben Zähler leer bzw. Readiness konservativ **Pilot**.

## 4. UI

### `/admin/gtm`

- **Product Readiness Overlay:** pro Segment (30 Tage): Anfragen, Qualifizierte, Pipedrive-Deals (neu), dominante Readiness-Klasse, Aufschlüsselung.
- **GTM × Readiness-Matrix:** Zeilen = Readiness-Klassen, Spalten = Segmente, Zellen = Anzahl **Anfragen** im 30-Tage-Fenster.

Daten kommen aus `GET /api/admin/gtm/summary` → Feld `product_bridge`.

### `/admin/leads`

Lead-Detail (`GET /api/admin/lead-inquiries/{id}`): Feld `product_bridge_hint` – Mandant, Readiness-Klasse, stichpunktartige Governance-Hinweise (Board-Schritt, KPI-Schritt, Systemanzahl). **Nur Lesen**, keine CRM-/Mandanten-Mutation.

## 5. Grenzen

- Mapping ist **manuell**; nicht jeder Lead hat Account oder Domain-Treffer.
- Kein Ersatz für CRM oder Mandanten-RLS-Audits.
- Klassen sind **heuristisch**; bei Bedarf Regeln in `gtmAccountReadiness.ts` verschärfen.
- Performance: pro Mandant im Mapping je ein API-Roundtrip beim Laden der GTM-Summary (kleine `entries`-Liste vorausgesetzt).

## 6. Verwandte Wellen

- Wave 32: [Weekly GTM Health Review](./wave32-weekly-gtm-health-review.md)
- Wave 31: [GTM Health & Readiness](./wave31-gtm-health-and-readiness.md)
