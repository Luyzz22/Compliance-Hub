# Wave 43 – Mandanten-Reminders & Follow-ups

Leichte **Erinnerungs-Hooks** pro Mandant für wiederkehrende Kanzlei-Arbeit – **kein** Jira/Trello, **kein** Workflow-Engine. Ziel: „Nicht vergessen“ (Review, Export, Follow-up-Notiz) sichtbar machen und mit einem Klick erledigen oder zurückstellen.

## Datenmodell

Persistiert in **`data/advisor-mandant-reminders.json`** (oder `ADVISOR_MANDANT_REMINDERS_PATH`, auf Vercel unter `/tmp`).

| Feld | Bedeutung |
|------|-----------|
| `reminder_id` | UUID |
| `tenant_id` | Mandanten-ID (`client_id`) |
| `category` | Siehe Kategorien unten |
| `due_at` | ISO-Zeitpunkt (Fälligkeit) |
| `status` | `open`, `done`, `dismissed` |
| `note` | Optional (besonders bei manuellen / Follow-up) |
| `source` | `auto` (Regel) oder `manual` |
| `created_at` / `updated_at` | ISO |

### Kategorien

| `category` | Typ | Bedeutung |
|------------|-----|-----------|
| `stale_review` | Auto | Review-Kadenz überfällig (wie Wave 40) |
| `stale_export` | Auto | Export-Kadenz oder kein Export erfasst |
| `high_gap_count` | Auto | Viele offene Prüfpunkte oder ≥2 mit hoher Dringlichkeit |
| `portfolio_attention` | Auto | Mandant erfüllt die **Attention-Queue-Kriterien** (Wave 41) |
| `follow_up_note` | Manuell | Freitext-Follow-up (Notiz Pflicht) |
| `manual` | Manuell | Kurzer manueller Reminder (Notiz optional) |

## Auto-Generierung

Bei jedem **`computeKanzleiPortfolioPayload`** (also jedem Laden von `GET /api/internal/advisor/kanzlei-portfolio`):

- Für jede Portfolio-Zeile und jede **Auto-Kategorie** wird geprüft, ob die Bedingung aktiv ist.
- **Neu:** Gibt es noch keinen **offenen** Auto-Reminder für `(tenant_id, category)`, wird einer mit Fälligkeit **Ende der lokalen Kalenderwoche (Sonntag 23:59:59)** angelegt.
- **Weg:** Ist die Bedingung nicht mehr erfüllt, wird ein offener Auto-Reminder für diese Kategorie auf **`done`** gesetzt (kein Löschen).

Manuelle Reminder werden von der Sync-Logik **nicht** verändert.

## API (intern, Lead-Admin)

| Methode | Pfad | Zweck |
|---------|------|--------|
| `GET` | `/api/internal/advisor/mandant-reminders` | Query: `client_id?`, `status?` (`open`/`done`/`dismissed`) |
| `POST` | `/api/internal/advisor/mandant-reminders` | Manuell anlegen: `client_id`, `category` (`manual` \| `follow_up_note`), `due_at`, optional `note` (bei `follow_up_note` Pflicht) |
| `PATCH` | `/api/internal/advisor/mandant-reminders` | `{ "reminder_id", "status": "done" \| "dismissed" }` |

Das **Portfolio** liefert zusätzlich eingebettet: `open_reminders`, Zähler **heute/überfällig** und **diese Woche**, sowie pro Zeile `open_reminders_count` und `next_reminder_due_at`.

## UI

- **Kanzlei-Cockpit:** Panel „Fällig heute / diese Woche“, Liste offener Reminder aus dem Portfolio, Aktionen Erledigt/Zurückstellen, kompaktes **manuelles** Anlegen (Mandant wählen, Fälligkeit, Notiz).
- **Mandanten-Export:** Für gewählte `client_id` offene Reminder listen und dieselben Aktionen.

## Unterschied zur Attention-Queue

| Aspekt | Attention-Queue (Wave 41) | Reminder (Wave 43) |
|--------|---------------------------|---------------------|
| Zweck | Priorisierte **Reihenfolge** „wer zuerst“ | **Zeitliche** und **inhaltliche** Erinnerung („bis wann“, Notiz) |
| Persistenz | Nur berechnet aus Live-Daten | **Gespeichert**, Status done/dismissed |
| Auto | Nein | Ja (Kadenz, Queue-Kriterium, Lücken) |
| Manuell | Nein | Ja (Anruf, Termin, Freitext) |

## Empfohlene Nutzung

- Wöchentlich Cockpit öffnen: Panel **diese Woche** abarbeiten, Erledigt setzen.
- Monatsende: offene Auto-Reminder prüfen; bei dauerhaft zurückgestellten Themen `dismissed` nutzen (erscheint nicht in „open“, Auto kann bei weiterhin gültiger Bedingung neu entstehen – bewusst einfach gehalten).

## Siehe auch

- `docs/advisors/wave41-kanzlei-review-playbook-and-queue.md`
- `docs/advisors/wave40-kanzlei-review-cadence-and-history.md`
- `frontend/src/lib/advisorMandantReminderRules.ts`
