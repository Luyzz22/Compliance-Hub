# Wave 31 – GTM Health & Pipeline Readiness

## Zweck

Auf dem [Founder Dashboard (Wave 29)](wave29-founder-dashboard.md) und der [Attribution-Schicht (Wave 30)](wave30-attribution-and-campaign-tracking.md) aufbauend: eine **ehrliche, regelbasierte Kompass-Ansicht** für frühe GTM-Phase — **kein** OKR-System, **kein** Board-BI.

Fragen, die in 1–2 Minuten beantwortet werden sollen:

- Wie stabil ist der **Eingang** (Webhooks, Noise)?
- Hängt **Triage**?
- Wie gesund ist der **CRM-Sync**?
- Passt **Pipeline** (qualifiziert → Deal) grob?
- Welche **Segmente** und **Kanäle** wirken ausgewogen vs. riskant?

## Wo im Produkt?

- **`/admin/gtm`** (oben): Block **GTM Health** (Kacheln), **Operative Hinweise**, erweiterte **Segment-Readiness-Tabelle**, **Attribution & Signalqualität (Top 3)**.
- Zugriff wie bisher: `LEAD_ADMIN_SECRET` / Session wie Lead-Inbox.

## Health-Indikatoren (Kacheln)

| Kachel | Signale | Status-Logik (Kurz) |
|--------|---------|---------------------|
| **Lead-Eingang** | Webhook-Fehlerquote & Spam-Anteil (30 Tage) | Schwellen in `gtmHealthThresholds.ts` (`GTM_HEALTH_WEBHOOK_RATE_*`, `GTM_HEALTH_SPAM_RATE_*`). Formular-Uptime wird **nicht** gemessen — Hinweis in der Kachel. |
| **Triage** | Anzahl Leads mit Status „Neu“, **älter als 3 Tage** (Einreichungsdatum) | ≥ 5 → issue, ≥ 2 → watch. |
| **CRM-Sync** | Anteil **Dead Letter + fehlgeschlagen** vs. **gesendet** (HubSpot/Pipedrive, 30 Tage, echte Connectors) | Nur ab Mindestdenominator (`GTM_HEALTH_CRM_BAD_RATIO_MIN_DENOM`). |
| **Pipeline** | Verhältnis **Pipedrive-Deals neu** / **qualifiziert** (30 Tage) | Nur wenn qualifiziert ≥ `GTM_HEALTH_PIPELINE_QUALIFIED_MIN`. |

Status je Kachel: **`good` | `watch` | `issue`** — qualitativ, keine gewichtete Gesamtnote.

## Operative Hinweise (SLA-Stil)

Aggregierte **Zähler** mit sachlichen Formulierungen (keine Zuschreibungen an Personen):

| Hint-ID | Bedeutung |
|---------|-----------|
| `untriaged_3d` | „Neu“-Leads älter als 3 Tage |
| `stuck_sync` | CRM-Job `failed`, letzter Versuch **> 24 h** her (`GTM_HEALTH_STUCK_SYNC_HOURS`) |
| `qualified_no_deal` | Triage qualifiziert / Abschluss-Interesse, **kein** Pipedrive-Deal (Sync), Einreichung **> 7 Tage** — **Proxy**, siehe Caveats |
| `attrib_noise` | Unter den Top-3-Quellen nach Volumen: Kanäle mit vielen Leads und sehr niedriger Qualifikationsquote (Heuristik) |

## Segment-Readiness

Pro Segment (inkl. „Sonstiges“): Anfragen und Qualifikation (30 Tage), **HubSpot gesendet**, **Pipedrive Touch** (gesendete Pipedrive-Jobs im Fenster), **Sync-Issues** (wie Wave 29), **dominante Attributions-Quellen** (Top 2 nach Volumen).

**Readiness-Hinweis (watch):**

- Kernsegmente mit **sehr wenig** Volumen (`GTM_HEALTH_SEGMENT_VOLUME_VERY_LOW`).
- **Viel Volumen**, aber **Qualifikationsquote** unter `GTM_HEALTH_SEGMENT_QUAL_RATIO_LOW` (ab `GTM_HEALTH_SEGMENT_VOLUME_MIN` Anfragen).

## Attribution Top 3 & Noise

Die drei stärksten Quellen (nach Leads 30 Tage) mit Qualifikationsquote. **Noise-Verdacht** ab Mindest-Leads und maximaler Qual-Quote (`GTM_HEALTH_ATTRIB_NOISE_*`).

## Technische Referenz

- Schwellen: `frontend/src/lib/gtmHealthThresholds.ts`
- Regeln & Texte: `frontend/src/lib/gtmHealthEngine.ts`
- Metrik-Vorbereitung: `frontend/src/lib/gtmDashboardAggregate.ts` (ruft `evaluateGtmHealth`)
- UI: `frontend/src/components/admin/GtmCommandCenterClient.tsx`

## Interpretation & Caveats

- **Frühphase:** Wenig Daten → viele Kacheln bleiben „OK“; Hinweise sind **advisory**.
- **Kein Qualifizierungszeitpunkt:** „Qualifiziert ohne Deal > 7 Tage“ nutzt **Einreichungsalter**, nicht das Datum der Triage-Änderung — kann **über- oder unterschätzen**.
- **Deals:** nur **Pipedrive-Sync** mit `deal_action === "created"` im 30-Tage-Fenster (wie bestehendes Dashboard).
- **Retries:** „Stuck sync“ zählt Jobs im Status `failed` mit altem `last_attempt_at` — Dispatcher-Verhalten kann abweichen.

## Ausblick

Schwellen anpassen, wenn Volumen steigt; optional später echte **Triage-Timestamps** oder **HubSpot-Property-Mapping** aus Wave 30/28 — weiterhin ohne Drittanbieter-Attribution-Stack.

## Ergänzung (Wave 32)

- **`health_signal_counts`** im Dashboard-Snapshot: dieselben Rohzähler, die auch für **Alert-Checks** genutzt werden (`untriaged_over_3d`, CRM Dead Letter / Failed 30d, qualifiziert ohne Deal-Proxy, stuck failed sync bleibt in operativen Hinweisen).  
- **Wöchentliche Routine** und **HTTP-Alerts**: siehe [Wave 32 – Weekly GTM Health Review](wave32-weekly-gtm-health-review.md).  
- **Maschinenlesbarer Export:** `GET /api/admin/gtm/health-snapshot` (Auth wie Alert-Automation).
