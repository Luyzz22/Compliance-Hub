# 09 – Security-Hardening-Plan

**Bewertungsmaßstab:** Was hält einer Enterprise-Security-Review, einem
Datenschutz-Audit und einem Penetrationstest stand — nicht, was in einer Checkliste
abhakbar ist.

**Vorbemerkung:** Die Sicherheitsgrundlagen dieses Projekts sind für seine Reifestufe
**überdurchschnittlich**. Argon2id, konstantzeit-Vergleiche, HttpOnly+CSRF-Sessions,
Entra OIDC mit PKCE und `tid`/`oid`-Bindung, CSP mit Build-Gate, gepinnte
GitHub-Actions, Bandit/CodeQL/pip-audit/npm-audit in CI, OPA-Policy-Tests und ein
Postgres-RLS-Test in CI sind nichts Selbstverständliches. Die folgenden Befunde sind
gezielt und keine Generalkritik.

---

## Bewertungsübersicht

| Bereich | Reife | Blocker |
|---|---|---|
| Passwort-/Credential-Handling | 🟢 gut | — |
| Session-Management | 🟢 gut | — |
| SSO / OIDC | 🟢 gut | SAML fehlt (P1-15) |
| SCIM / Lifecycle | 🟡 vorhanden | Protokollkonformität nicht verifiziert |
| MFA | 🟡 funktional | **Secret-Ablage ungeschützt** (P0-9) |
| RBAC | 🟢 gut | Durchsetzung nicht endpunktweit verifiziert |
| Mandantenisolation | 🔴 | **Keine DB-Schranke, keine Negativtests** (P0-1, P0-12) |
| Secrets-Management | 🟡 | Kein Vault, keine Rotation |
| Verschlüsselung Transport | 🟢 gut | — |
| Verschlüsselung at rest | 🔴 | Evidence im Klartext; kein Deployment-Nachweis |
| Audit-Log-Integrität | 🟡 gut gedacht | ORM-seitig, kein externer Anker |
| Evidenzintegrität | 🔴 | **Kein Inhalts-Hash** (P0-4) |
| Upload-Sicherheit | 🔴 | **Kein Malware-Scan, kein Magic-Byte-Check** (P0-4) |
| API-Sicherheit | 🟡 | **Kein Rate Limiting** (P1-7) |
| Hintergrundjobs | 🔴 | **Kein Scheduler** (P0-6) |
| DR / Backup | 🔴 | **Nicht vorhanden** (P0-7) |
| Monitoring / Alerting | 🟡 | OTel vorhanden, kein Alerting-Konzept |
| Admin-Oberflächen | 🟡 | Statischer ENV-Admin-Key ohne MFA |
| Demo-Umgebung | 🟢 gut | Eigener Key-Pool + Tenant-Allowlist |
| Supply Chain | 🟢 sehr gut | SBOM/Signierung fehlen (P2-8) |

---

## 1. MFA

**Ist:** Eigene RFC-6238-TOTP-Implementierung
(`app/services/enterprise_governance_service.py:196–220`), Backup-Codes,
Enroll-/Verify-/Status-/Step-up-/Reset-Endpunkte (`app/main.py:8690–8770`),
Tabellen `mfa_factors` und `mfa_backup_codes`.

**Befund 1 — 🔴 TOTP-Secret ohne Verschlüsselung.**
Ein Datenbank-Dump kompromittiert alle zweiten Faktoren aller Mandanten. Das entwertet
MFA vollständig und ist in jeder Security-Review ein Sofort-Fund.
→ **P0-9.** AES-GCM-Envelope-Encryption über `app/security_credentials.py`, Schlüssel
aus Key Vault, `key_id` mitspeichern für Rotation.

**Befund 2 — 🟡 Eigenimplementierung von Kryptografie.**
Die HOTP/TOTP-Berechnung ist selbst geschrieben. Der Algorithmus ist einfach und
korrekt umgesetzt, aber Prüfer bewerten Eigenimplementierungen kritisch. Zu prüfen:
Replay-Schutz (wird ein bereits verwendeter Code abgelehnt?) und Toleranzfenster.
→ **P1.** Entweder auf `pyotp` wechseln oder Replay-Schutz explizit ergänzen und
dokumentieren.

**Befund 3 — 🟡 Kein WebAuthn/FIDO2.**
Phishing-resistente Faktoren werden von Behörden und Banken zunehmend verlangt.
→ **P2.**

**Befund 4 — 🟡 MFA-Erzwingung nicht durchgängig.**
Es gibt einen Step-up-Endpunkt, aber keine erkennbare Policy „diese Aktionen erfordern
frische MFA". Kandidaten: Mandantenlöschung, API-Key-Erzeugung, Rollenänderung,
Evidence-Löschung, Trust-Center-Veröffentlichung.
→ **P1.** Dependency `require_recent_mfa(max_age_minutes=15)`.

---

## 2. SSO, SAML, SCIM

**Ist:** Entra OIDC mit Code+PKCE, verschlüsselter State/Nonce-Transaktion,
mandantenspezifischer Token-Prüfung, unveränderlicher `tid`+`oid`-Bindung und
App-Role-Gate. Lokale Rolle bleibt maßgeblich, E-Mail-Claims gewähren keinen Zugriff.
**Das ist sauber gebaut.**

**Befund 1 — 🟡 Nur Entra.** Okta, Keycloak, Ping und generisches OIDC fehlen; SAML 2.0
fehlt vollständig. In DACH ist Entra sehr verbreitet, aber öffentliche Hand und
Konzerne verlangen häufig SAML. → **P1-15.**

**Befund 2 — 🟡 SCIM-Konformität unklar.** `SCIMProvisioningService` implementiert
provision/update/disable/deprovision, aber es ist nicht erkennbar, ob ein
SCIM-2.0-konformer Endpunkt (`/scim/v2/Users`, `/Groups`, Filter, PATCH-Semantik)
existiert. Ohne den kann Entra nicht automatisch provisionieren. → **P1 verifizieren.**

**Befund 3 — 🔴 Legacy-SSO-Callback.** `COMPLIANCEHUB_ALLOW_LEGACY_SSO_CALLBACK` und
`SSOCallbackService.process_sso_login` erlauben attributbasierte Anmeldung. In
Produktion ist der Pfad laut Readiness-Doku deaktiviert — das ist **eine
Konfigurationsentscheidung, kein Code-Zwang**.
→ **P0.** Pfad in `prod` hart entfernen, nicht nur flaggen.

---

## 3. Rollenmodell

**Ist:** 10 Rollen, 47 Permissions, Rollen-Permission-Mapping (`app/rbac/`),
zusätzlich OPA-Policies, SoD-Policies, Approval-Requests, Access Reviews,
Privileged-Action-Events. Sehr vollständig.

**Befund 1 — 🟠 Durchsetzung nicht flächendeckend nachweisbar.** Bei ~250 Endpunkten in
`app/main.py` ist nicht ohne Weiteres verifizierbar, ob jeder die passende Permission
prüft. Eine einzige vergessene Prüfung ist eine Privilege-Escalation.
→ **P1.** Test, der alle Routen aus dem OpenAPI-Schema aufzählt und für jede eine
explizite Permission-Zuordnung erzwingt (Allowlist für bewusst öffentliche Routen).
Neue Endpunkte ohne Zuordnung lassen die CI fehlschlagen.

**Befund 2 — 🟠 `x-opa-user-role`-Header.** `get_optional_opa_user_role_header` erlaubt
dem Client, seine Rolle selbst zu behaupten. Standardmäßig aus
(`COMPLIANCEHUB_OPA_TRUST_CLIENT_ROLE_HEADER=false`) — aber die Existenz des Schalters
ist ein Risiko.
→ **P1.** In `prod` unabhängig von der ENV ignorieren.

**Befund 3 — 🔴 Advisor-Autorisierung.** `require_advisor_api_access`
(`app/security.py:80–110`) prüft: globaler API-Key + selbstdeklarierter
`x-advisor-id`-Header + optionale ENV-Allowlist. Wer einen globalen Key besitzt, kann
sich als beliebiger Advisor ausgeben, sofern keine Allowlist gesetzt ist — und die ist
optional.
→ **P0.** Advisor-Zugriff auf Session-Auth umstellen; Allowlist verpflichtend;
Zuordnung ausschließlich über `advisor_tenants` in der DB.

---

## 4. Break-Glass-Konten

**Ist:** Nicht vorhanden. `COMPLIANCEHUB_ADMIN_API_KEYS` ist ein statischer ENV-String
ohne Ablauf, Rotation, MFA oder Vier-Augen-Prinzip und autorisiert die Anlage
beliebiger Mandanten.

→ **P1.** Break-Glass-Modell:
- Dedizierte Konten, normal deaktiviert
- Aktivierung nur mit Vier-Augen-Freigabe (`approval_requests` ist vorhanden)
- Zeitlich begrenzte Gültigkeit
- Jede Aktion in `privileged_action_events` **und** dem Kunden sichtbar
- Automatische Benachrichtigung an einen definierten Verteiler bei Aktivierung
- Quartalsweise Überprüfung

---

## 5. Session-Management

**Ist:** 🟢 Gut. Opake Tokens, DB-gestützt, TTL 8 h (konfigurierbar), Revokation,
HttpOnly-Cookie + separates CSRF-Cookie (Double-Submit),
`Cache-Control: private, no-store` auf allen Antworten.

**Befund 1 — 🟡 Keine Rotation nach Privilegienwechsel.** Nach Login-Step-up oder
Rollenänderung sollte die Session-ID rotieren (Session-Fixation-Härtung). → **P2.**

**Befund 2 — 🟡 Keine Anzeige/Verwaltung aktiver Sessions.** Nutzer sollten ihre
aktiven Sitzungen sehen und einzeln beenden können. → **P2.**

**Befund 3 — 🟡 Kein Idle-Timeout.** 8 h absolute TTL ohne Inaktivitätsgrenze ist für
ein GRC-Tool lang. → **P2.** Zusätzlich 30–60 min Idle-Timeout.

---

## 6. Mandantenisolation

Siehe `01` §5, `05` §9, `07` P0-1 und P0-12. Kurzfassung:

- Applikationsseitige Filterung: konsistent umgesetzt.
- DB-seitige Schranke: **nicht wirksam**.
- Negativtests: **nicht vorhanden**.

**Dies ist der wichtigste Sicherheitsbefund des gesamten Reviews.** Er ist nicht
deshalb kritisch, weil ein konkreter Bug bekannt wäre, sondern weil bei 409 Modulen und
~250 Endpunkten ohne DB-Schranke und ohne Negativtests **die Abwesenheit eines Bugs
nicht nachweisbar** ist. Genau diesen Nachweis verlangt jeder Datenschutzbeauftragte.

---

## 7. Secrets-Management

| Befund | Bewertung | Maßnahme |
|---|---|---|
| Alle Secrets als Klartext-ENV | 🟡 | Key Vault / Vault-Integration — P1 |
| Kein Rotationsmechanismus | 🟡 | Rotationsrunbook + `expires_at` auf `tenant_api_keys` — P1 |
| `hash_api_key` = SHA-256 ohne Salt | 🟡 | Für hochentropische Keys vertretbar; **Mindestentropie bei der Erzeugung erzwingen** (≥ 32 Byte CSPRNG) — P1 |
| `tenant_api_keys` ohne `expires_at` | 🟠 | Ablauf + Rotationshinweis — P1 |
| `COMPLIANCEHUB_ADMIN_API_KEYS` statisch | 🔴 | Siehe §4 — P1 |
| GitHub Secret Scanning + Push Protection aktiv | 🟢 | Beibehalten |
| `AuthContext.api_key` mit `exclude=True, repr=False` | 🟢 | **Vorbildlich** — Credential landet nie in Logs |

---

## 8. Verschlüsselung

**Transport:** 🟢 HSTS (prod), HTTPS-Zwang für Azure OpenAI, TLS für Temporal.

**At rest:** 🔴
- Evidence-Dateien: Klartext im Dateisystem.
- DB: keine applikationsseitige Feldverschlüsselung; Plattformverschlüsselung nicht
  belegbar, weil kein Deployment-Artefakt existiert.
- TOTP-Secrets: unverschlüsselt (§1).

→ **P0-4** (Blob-Backend mit SSE), **P0-9** (TOTP), **P0-7** (Deployment mit
belegbarer Plattformverschlüsselung).

**BYOK/CMK:** 🔴 nicht vorhanden, nicht vorbereitet. Für Modus 2/3 erforderlich.
→ **P2-10.** Schlüsselabstraktion einziehen, damit BYOK später kein Umbau wird.

---

## 9. Append-only-Audit-Logs

**Ist:** `app/audit_append_only.py` blockiert UPDATE/DELETE auf `AuditLogTable` im
SQLAlchemy-`before_flush`. Hash-Kette mit `verify_integrity()`.

**Befund 1 — 🟠 Nur ORM-seitig.** Direkter SQL-Zugriff, DBA, Bulk-Statement,
Backup-Restore umgehen den Guard vollständig.
→ **P1.** DB-seitig durchsetzen: `REVOKE UPDATE, DELETE ON audit_logs FROM
compliancehub_runtime_app;` plus BEFORE-Trigger, der UPDATE/DELETE mit Ausnahme des
Retention-Systemkontexts abweist.

**Befund 2 — 🟠 Kein externer Anker.** → **P1-16.**

**Befund 3 — 🔴 Konflikt mit Art. 5(1)(e) DSGVO.** Unbegrenzt wachsende, nicht
löschbare Logs mit `ip_address`, `user_agent` und vollständigen `before`/`after`-JSONs.
→ **P0-5.** Kontrollierter Retention-Pfad mit Metadaten-Nachweis.

**Befund 4 — 🟠 Datenminimierung in `before`/`after`.** Voll-Serialisierung von
Entitäten mit Freitextfeldern kann personenbezogene Daten unlöschbar konservieren.
→ **P2-7.** Feldbasierte Allowlist je Entitätstyp.

---

## 10. Evidenzintegrität und Uploads

Siehe `07` P0-4. Drei Befunde, alle 🔴:

1. **Kein Inhalts-Hash** in `evidence_files` → Integrität nicht nachweisbar.
2. **Kein Malware-Scan** → Verteilung von Schadsoftware an andere Nutzer desselben
   Mandanten möglich; sofortiger Ausschlussgrund in jeder Enterprise-Review.
3. **Typprüfung spoofbar** — `resolve_content_type` (`app/services/evidence_service.py:53`)
   vertraut dem `Content-Type`-Header oder der Dateiendung. Es findet keine
   Magic-Byte-Prüfung statt.

**Positiv:** `_validate_storage_key` verhindert Path Traversal sauber; Originaldateinamen
werden nicht als Pfad verwendet; Größenlimit vorhanden; Rollback bei DB-Fehler löscht
die Datei wieder. Die Grundstruktur ist richtig — es fehlen drei Bausteine.

---

## 11. API-Sicherheit

| Befund | Bewertung | Maßnahme |
|---|---|---|
| **Kein Rate Limiting** | 🔴 | Brute-Force auf Login/API-Keys, Ressourcenerschöpfung, Kostenexplosion bei LLM-Endpunkten — **P1-7** |
| **Keine Idempotency-Keys** auf schreibenden Endpunkten | 🟠 | Doppelte Incidents/Tasks bei Netzwerk-Retry — P1-7 |
| CORS mit `allow_credentials=False` und Origin-Allowlist | 🟢 | Korrekt |
| TrustedHost-Middleware | 🟢 | Korrekt, wenn konfiguriert |
| OpenAPI/Docs in prod deaktiviert | 🟢 | Korrekt |
| Security-Header ohne Response-Buffering | 🟢 | Sauber gelöst |
| Kein API-Versionierungs-/Deprecation-Konzept | 🟡 | `/api/v1` als Präfix vorhanden, Policy fehlt — P2 |
| Fehlermeldungen ohne Provider-Details | 🟢 | Korrekt für Azure OpenAI |

**Zu prüfen:** Ob Fehlerantworten an anderen Stellen Stacktraces oder interne Pfade
preisgeben. Test ergänzen, der in `prod` jede 5xx-Antwort auf generische Inhalte prüft.

---

## 12. Hintergrundjobs und Fristen

Siehe `07` P0-6. Kernpunkt: **Ein Compliance-Produkt, dessen Fristenüberwachung ohne
externe Einrichtung nicht läuft und für den Kunden nicht sichtbar ist, gibt ein
Versprechen, das es nicht hält.**

Zusätzlich erforderlich:
- Deterministische Fristenberechnung mit expliziter Zeitzone (Deadlines in DACH sind
  faktisch `Europe/Berlin`-relevant, gespeichert wird UTC — die Umrechnung muss
  bewusst und getestet sein)
- Retry mit Backoff und Dead-Letter-Queue
- Idempotenz bei Job-Wiederholung
- Leader-Election bei mehreren Instanzen

---

## 13. Disaster Recovery und Backup

🔴 **Nicht vorhanden**, weil kein Deployment existiert.

Zielzustand (Modus `Standard DACH`):

| Parameter | Ziel |
|---|---|
| RPO | ≤ 15 min (PITR) |
| RTO | ≤ 4 h |
| Backup-Aufbewahrung | 35 Tage PITR + monatliche Vollsicherung 12 Monate |
| Georedundanz | Innerhalb EU |
| Restore-Test | Quartalsweise, dokumentiert |
| Evidence-Storage | Soft Delete 30 Tage + Versioning + Immutability für Audit-Exporte |
| Notfallkommunikation | Runbook mit Kontakten und Eskalation |

Der **dokumentierte Restore-Test** ist der eigentliche Nachweis — ein Backup ohne
getesteten Restore ist in einer Prüfung wertlos. → **P0-7.**

---

## 14. Monitoring und Alerting

**Ist:** OpenTelemetry API/SDK, `TelemetryMiddleware`, `app/telemetry/tracing.py`,
optionales LangSmith-Tracing, `service_health_snapshots`/`service_health_incidents`,
`health_monitor.py`.

**Befunde:**
- 🟡 Kein Alerting-Ziel definiert (kein PagerDuty/Opsgenie/Teams-Webhook)
- 🟡 Keine Security-Alerts (fehlgeschlagene Logins, Rechteänderungen, Massenexporte,
  Audit-Ketten-Bruch)
- 🟡 Kein SIEM-Export der Audit-Logs
- 🔴 **LangSmith-Tracing** (`app/services/langsmith_tracing.py`) — falls aktiviert,
  fließen Prompt-Inhalte an einen **US-Anbieter**. Muss in die Vendor-Matrix und in
  den Souveränitätsmodus (P0-3) aufgenommen und in `eu_sovereign`/`strict_sovereign`
  hart deaktiviert werden.

→ **P1.** Alerting-Konzept + Security-Events; **P0-3** um LangSmith erweitern.

---

## 15. Admin-Oberflächen

| Befund | Bewertung |
|---|---|
| Admin-Session über geteiltes Secret (`app/api/admin/session`, `lib/leadAdminAuth.ts`) | 🟠 Kein MFA, kein individuelles Konto, keine Rollentrennung |
| `COMPLIANCEHUB_ADMIN_API_KEYS` für Tenant-Provisionierung | 🔴 Siehe §4 |
| `sbs_domain_auto_admin.py` — automatische Admin-Vergabe nach E-Mail-Domain | 🔴 **Kritisch prüfen** |

Zu `sbs_domain_auto_admin`: Wenn eine E-Mail-Domain automatisch Admin-Rechte auslöst,
ist die Sicherheit an die Kontrolle über eine Domain und die Zuverlässigkeit der
E-Mail-Verifikation gekoppelt. Das ist ein bekanntes Muster für
Privilege-Escalation-Findings.
→ **P0.** Verhalten prüfen; in `prod` nur mit expliziter Allowlist und
verifizierter Domain zulassen, besser vollständig deaktivieren.

---

## 16. Demo-Umgebungen

🟢 **Gut gelöst.** Eigener Key-Pool (`COMPLIANCEHUB_DEMO_SEED_API_KEYS`),
verpflichtende Tenant-Allowlist (`ensure_demo_tenant_seed_allowed` wirft 403, wenn
keine gesetzt ist), `demo_tenant_guard` verhindert Schreibzugriffe auf
Nicht-Demo-Mandanten, `tenants.is_demo`/`demo_playground`-Flags,
`COMPLIANCEHUB_PUBLIC_DEMO_ENABLED` standardmäßig aus.

**Verbleibend:** 🟡 Klarstellen, dass Demo-Daten synthetisch sind
(`demo_synthetic_runtime_events.py` deutet darauf hin) und dass kein Pfad existiert,
über den Produktivdaten in eine Demo gelangen.

---

## 17. Testdatenstrategie

**Befunde:**
- 🟡 Der DB-Default `test_compliancehub.db` legt nahe, dass Entwicklung und Test
  dieselbe Datei nutzen. Sauberer: dedizierte Test-DB je Lauf.
- 🟡 Keine erkennbare Regel gegen Produktivdaten in Test-/Demo-Umgebungen.
- 🟢 Seed-Skripte erzeugen synthetische Daten.

→ **P2.** Kurze Richtlinie „Keine Produktivdaten außerhalb der Produktion" in
`SECURITY.md`, plus Datengenerator statt Kopie.

---

## 18. Sofortmaßnahmen (erste zwei Wochen)

| # | Maßnahme | Aufwand | Wirkung |
|---|---|---|---|
| 1 | `NEXT_PUBLIC_API_KEY`/`NEXT_PUBLIC_TENANT_ID` aus `.env.pilot.example` entfernen + Build-Gate | 2 h | Verhindert Credential-Leak bei jedem Piloten |
| 2 | `app/tenant_middleware.py` löschen | 1 h | Entfernt einen latenten Cross-Tenant-Bypass |
| 3 | `get_async_db` fail-closed auf `AuthContext` umstellen | 4 h | Beseitigt Sessions ohne Mandantenschranke |
| 4 | TOTP-Secrets verschlüsseln | 1 PT | Rettet die MFA-Aussage |
| 5 | `VVTExport` umbenennen | 2 h | Beseitigt eine irreführende Bezeichnung |
| 6 | Advisor-Allowlist verpflichtend machen | 4 h | Schließt die schwächste Autorisierungsstelle |
| 7 | Cross-Tenant-Negativtests (erste Tranche) | 2 PT | Erzeugt den verkaufbaren Nachweis |
| 8 | `sbs_domain_auto_admin` in `prod` deaktivieren | 2 h | Schließt möglichen Privilege-Escalation-Pfad |
| 9 | LangSmith in die Vendor-Matrix + Modus-Filter | 4 h | Schließt eine unbemerkte US-Datenroute |
| 10 | Legacy-SSO-Callback in `prod` hart entfernen | 4 h | Macht aus einer Konfiguration einen Code-Zwang |

**Gesamt: ca. 8 Personentage** für eine erhebliche Verbesserung der Sicherheitslage
und der Claim-Festigkeit. Die Punkte 1, 2, 3, 5, 8, 9 und 10 sind in diesem Change-Set
bereits umgesetzt — siehe `00-executive-readiness-verdict.md` §C.
