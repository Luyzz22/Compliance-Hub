# Wave 60 – Article 50 & GDPR Transparency Assurance

## Ziel und Kontrollgrenze

Wave 60 ergänzt das KI-System-Register um ein persistentes, mandantenfähiges Nachweisregister für
Transparenzkontrollen. Es bewertet keine Rechtskonformität automatisch. Die Anwendung zeigt offen,
welche Scoping-, Implementierungs-, Evidenz- oder Review-Schritte noch fehlen.

Die Kontrollbibliothek bildet sechs getrennte Sachverhalte ab:

| Kontrollschlüssel | Operativer Gegenstand | Rechtsbezug |
| --- | --- | --- |
| `ai_interaction_disclosure` | Offenlegung der KI-Interaktion ab der ersten Interaktion | EU AI Act Art. 50(1) |
| `synthetic_content_marking` | Maschinenlesbare Kennzeichnung künstlicher/manipulierter Inhalte | EU AI Act Art. 50(2) |
| `emotion_biometric_notice` | Information bei Emotionserkennung/biometrischer Kategorisierung | EU AI Act Art. 50(3) |
| `deepfake_disclosure` | Offenlegung künstlich erzeugter/manipulierter Bild-, Audio- und Videoinhalte | EU AI Act Art. 50(4) |
| `public_interest_text_review_or_disclosure` | Offenlegung oder substanzielle menschliche Prüfung unter redaktioneller Verantwortung | EU AI Act Art. 50(4) |
| `gdpr_transparency_notice` | Referenz auf die einschlägige Datenschutzinformation | DSGVO Art. 12–14, ggf. Art. 22 |

Die EU-Kommission beschreibt den 2. August 2026 als Beginn der Anwendbarkeit der
Art.-50-Transparenzpflichten. Die UI zeigt diesen Termin und die verbleibenden beziehungsweise
verstrichenen Tage, ohne daraus eine rechtliche Einzelfallentscheidung abzuleiten.

## Evidenz- und Freigaberegeln

- Status je Kontrolle: `not_assessed`, `not_applicable`, `planned`, `implemented`, `verified`.
- `verified` erfordert eine Evidenzreferenz, geklärte Provider-/Deployer-Rolle, Control Owner,
  unabhängigen Reviewer, Prüfdatum und nächsten Review-Termin.
- `not_applicable` erfordert immer eine konkrete Begründung.
- Control Owner und Reviewer müssen verschieden sein (Vier-Augen-Prinzip).
- Alle sechs Kontrollschlüssel müssen bei jedem Speichern genau einmal enthalten sein.
- `expected_version` verhindert das unbemerkte Überschreiben eines zwischenzeitlich geänderten
  Assessments; veraltete Writes enden mit HTTP 409.
- Das Readiness-Scoring ist ein operativer Reifeindikator, keine Konformitätsfeststellung:
  `planned=25`, `implemented=75`, `verified=100`; begründet nicht anwendbare Kontrollen werden aus
  dem Nenner genommen. Ein vollständig leerer oder ungeklärter Scope bleibt `requires_scope`.

## Persistenz und Tenant-Isolation

Die Migration `20260502_ai_transparency_assurance` legt zwei normalisierte Tabellen an:

- `ai_transparency_assessments`: Scope, Owner/Reviewer, Review-Kadenz, Version und Änderungsmetadaten;
- `ai_transparency_controls`: genau eine status- und evidenzfähige Zeile je Kontrollschlüssel.

Jede Repository-Abfrage filtert explizit nach `tenant_id`; Child-Zeilen tragen den Tenant ebenfalls.
Negative API-Tests belegen, dass ein anderer Mandant weder Assessment noch Systemreferenz erhält.
Das ist Anwendungsschicht-Evidenz. Der weiterhin geltende Enterprise-Exit-Gate verlangt zusätzlich
Tests gegen eine produktionsäquivalente PostgreSQL-Konfiguration und eine freigegebene RLS-Strategie
für diese Core-Domäne.

## APIs und Berechtigungen

| Methode | Route | Permission |
| --- | --- | --- |
| GET | `/api/v1/transparency-assurance` | `view_transparency_assurance` |
| GET | `/api/v1/ai-systems/{id}/transparency-assurance` | `view_transparency_assurance` |
| PUT | `/api/v1/ai-systems/{id}/transparency-assurance` | `manage_transparency_assurance` |

Contributor, Auditor und höhere operative Rollen können lesen; Board Member erhalten die
Portfolioansicht. Nur Compliance Officer und die davon erbenden Rollen dürfen attestieren. Viewer
und Editor können keine Evidenz freigeben.

Jede Änderung erzeugt:

1. einen hashverketteten GoBD-orientierten Audit-Eintrag mit Status- und Presence-Signalen; und
2. ein normalisiertes Audit Event für operative Auswertungen.

Assessment, normalisiertes Audit Event und hashverketteter Audit-Eintrag werden in derselben
Datenbanktransaktion geschrieben. Schlägt ein Teil fehl, wird die gesamte Änderung zurückgerollt.

Aus Datenschutzgründen enthält der hashverkettete Before/After-Snapshot weder Evidenzpfade noch
Reviewer- oder Owner-Bezeichnungen. Im Assessment selbst sollen Funktionsrollen und kontrollierte
Dokument-IDs statt unnötiger personenbezogener Daten, Secrets oder frei zugänglicher URLs verwendet
werden.

## UI

`/tenant/transparency-assurance` liefert:

- Regulatory Clock und Portfolio-Readiness;
- alle KI-Systeme einschließlich vollständig unbewerteter Systeme;
- explizite Scope-/Overdue-/Verification-Posture;
- sechs barrierearm beschriftete Kontroll-Editoren;
- client- und serverseitige Evidenzvalidierung;
- Link auf die zugrunde liegende EU-Kommissionsquelle und einen sichtbaren Legal Boundary.

Die Seite ist eine Enterprise-Route und bleibt im `public_site`-Releaseprofil nicht veröffentlicht.

## Verifikationsumfang

- Pydantic-Negativtests für fehlende Evidenz, fehlende Ausnahmebegründung, naive Zeitstempel,
  fehlende Wiedervorlage und verletzte Funktionstrennung;
- API-Tests für Default-Lücken, Scoring, RBAC, Cross-Tenant-Isolation, 409-Konflikte und
  Audit-Datenminimierung;
- React-Tests für Kontrollvollständigkeit, lokale Evidenzvalidierung und versioniertes Speichern;
- Ruff, vollständige Backend-Tests, Frontend-Lint/Unit/Build, CSP-/Runtime-Storage-Gates und
  Browser-Verifikation vor Merge.

## Bewusst offene Grenzen

- Eine Evidenzreferenz beweist nicht selbst die Echtheit oder inhaltliche Eignung des Artefakts.
- Das Register testet nicht automatisch, ob ein konkretes Wasserzeichen oder maschinenlesbares
  Kennzeichnungsformat technisch wirksam ist.
- Die Anwendbarkeit von Ausnahmen, DSGVO-Rechtsgrundlagen sowie Art. 22 und die Qualität einer
  „substanziellen“ redaktionellen Prüfung bleiben fachlich und rechtlich zu prüfen.
- Retention, Legal Hold, DSAR, DPIA/FRIA, Löschung und produktionsäquivalente RLS-Evidenz bleiben
  separate, weiterhin verbindliche Enterprise-Gates.

## Primärquellen

- [EU-Kommission – FAQ zu Art. 50 Transparenzpflichten](https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act)
- [EU-Kommission – Veröffentlichung der Art.-50-Leitlinien, 20. Juli 2026](https://digital-strategy.ec.europa.eu/en/news/commission-publishes-guidelines-transparency-obligations-providers-and-deployers-certain-ai-systems)
- [Verordnung (EU) 2024/1689 – EU AI Act](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)
- [Verordnung (EU) 2016/679 – DSGVO](https://eur-lex.europa.eu/eli/reg/2016/679/oj)
