# Wave 61 - DSFA und FRIA Impact Assessment

## Ziel und Kontrollgrenze

Wave 61 schließt die in Wave 60 dokumentierte Lücke für Datenschutz-Folgenabschätzung (DSFA/DPIA)
und Fundamental Rights Impact Assessment (FRIA). Die Funktion strukturiert Scope, Risiken,
Schutzmaßnahmen, Konsultationsstatus und unabhängige Review-Evidenz je registriertem KI-System.

Sie trifft keine automatische Rechtsentscheidung, ersetzt keine Datenschutzbeauftragten,
Rechtsberatung oder Behördenkonsultation und erklärt ein System nicht automatisch für zulässig.

## Primärquellen und abgebildete Prüffelder

- DSGVO Art. 35: Beschreibung und Zwecke, Erforderlichkeit und Verhältnismäßigkeit, Risiken für
  Rechte und Freiheiten sowie geplante Abhilfen, Garantien und Sicherheitsmaßnahmen.
- DSGVO Art. 36: Status einer gegebenenfalls erforderlichen vorherigen Konsultation.
- EU AI Act Art. 27: Einsatzprozess, Zeitraum und Häufigkeit, betroffene Personen und Gruppen,
  Grundrechtsrisiken, Human Oversight sowie Governance-, Beschwerde- und Abhilfemechanismen.

Die acht Assessment-Felder sind eine operative Strukturierung dieser Gegenstände. Ob DSFA oder
FRIA im Einzelfall erforderlich ist, bleibt eine dokumentierte menschliche Scope-Entscheidung.

## Datenmodell

`ai_impact_assessments` speichert pro Tenant und KI-System:

- getrennten DSFA- und FRIA-Scope (`undetermined|required|not_required`)
- Einsatzkontext, Lifecycle, Residualrisiko und Konsultationsstatus
- Assessment Owner und unabhängige Review-Funktion
- Datenschutzbeauftragten-Einbindung und Betroffenenbeteiligung
- Prüf-, Freigabe- und Wiedervorlagetermine
- Optimistic-Locking-Version und minimierte Änderungsmetadaten

`ai_impact_assessment_sections` speichert genau eine Zeile je Prüffeld mit Status, fachlicher
Zusammenfassung, Begründung und kontrollierter Evidenzreferenz.

## Harte Validierungsregeln

- Alle acht Prüffelder müssen bei jedem Write genau einmal enthalten sein.
- `reviewed` erfordert Zusammenfassung und Evidenzreferenz.
- `not_applicable` erfordert eine konkrete Begründung.
- Nicht erforderlicher DSFA- oder FRIA-Scope erfordert eine Scope-Begründung.
- Eine interne Freigabe erfordert geklärten Scope, Funktionsrollen, verschiedene Owner/Reviewer,
  Review- und Wiedervorlagetermine und bei DSFA-Scope dokumentierte DSB-Einbindung.
- Bei erforderlichem Scope müssen alle Prüffelder reviewed sein.
- Hohes Residualrisiko kann erst nach dokumentiert abgeschlossenem Konsultationsstatus intern
  freigegeben werden.
- `expected_version` verhindert stilles Überschreiben paralleler Bearbeitungen.

## API und RBAC

| Methode | Route | Berechtigung |
| --- | --- | --- |
| GET | `/api/v1/impact-assessments` | `view_impact_assessments` |
| GET | `/api/v1/ai-systems/{id}/impact-assessment` | `view_impact_assessments` |
| PUT | `/api/v1/ai-systems/{id}/impact-assessment` | `manage_impact_assessments` |

Contributor, Auditor, Compliance Officer und höhere operative Rollen können lesen. Board Member
sehen die Portfolio-Posture. Schreiben ist Compliance Officer und erbenden Rollen vorbehalten.

## Audit und Datenminimierung

Assessment, normalisiertes Audit Event und hashverketteter GoBD-orientierter Audit-Eintrag werden
innerhalb einer Transaktion geschrieben. Der Hash-Audit-Snapshot enthält nur Status-, Presence- und
Versionssignale. Freitexte, Evidenzpfade und Funktionsbezeichnungen werden nicht dupliziert.

Die UI empfiehlt Funktionsrollen und kontrollierte Dokument-IDs statt Personennamen, frei
zugänglicher URLs oder sensibler Inhalte.

## UI

`/tenant/impact-assessments` liefert:

- Portfolio-Posture mit Scope-, Review- und Konsultationsblockern
- Systemauswahl mit klarer aktueller Position
- getrennte Scope-Entscheidungen für DSFA und FRIA
- acht zugängliche Assessment-Editoren
- Lifecycle-, Residualrisiko- und Konsultations-Gates
- lokale Validierung vor dem API-Write und konfliktgeschütztes Speichern
- sichtbare Primärquellen und Legal Boundary direkt am Workflow

## Bewusst offene Gates

- Die fachliche Richtigkeit einer Evidenzreferenz wird nicht automatisch bewiesen.
- Rechtsgrundlagen, Betroffenenkreise, Verarbeitungsverzeichnis und Transferbewertung müssen
  organisations- und einsatzbezogen geprüft werden.
- Eine Behördenkonsultation wird dokumentiert, aber nicht automatisch ausgelöst.
- Produktionsäquivalente PostgreSQL-RLS-Evidenz, Retention, Legal Hold und Löschprozesse bleiben
  separate Release- und Betriebsnachweise.
