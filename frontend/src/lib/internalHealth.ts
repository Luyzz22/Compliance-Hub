/**
 * Interne Betriebs-/Monitoring-Health ( später GET /api/internal/health mit X-HEALTH-KEY serverseitig;
 * Browser ruft typischerweise einen mandanten-auth-geschützten BFF auf ).
 */

export type HealthStatus = "up" | "degraded" | "down";

export interface ServiceHealth {
  app: HealthStatus;
  db: HealthStatus;
  externalAiProvider: HealthStatus;
}

export interface InternalHealthPayload extends ServiceHealth {
  timestamp: string;
}

/** Mappt JSON mit snake_case vom Backend auf das Frontend-ViewModel. */
export function mapInternalHealthJson(body: {
  app: HealthStatus;
  db: HealthStatus;
  external_ai_provider: HealthStatus;
  timestamp: string;
}): InternalHealthPayload {
  return {
    app: body.app,
    db: body.db,
    externalAiProvider: body.external_ai_provider,
    timestamp: body.timestamp,
  };
}

/**
 * Stub: später z. B. mandanten-auth-geschützter Proxy → GET /api/internal/health.
 * Beispiel-Payload mit `externalAiProvider: "degraded"` zeigt Governance-Hinweis in der UI.
 */
export async function fetchHealthStatus(): Promise<InternalHealthPayload> {
  await Promise.resolve();
  return {
    app: "up",
    db: "up",
    externalAiProvider: "degraded",
    timestamp: new Date().toISOString(),
  };
}

export function governanceServiceHealthHint(health: ServiceHealth): string | null {
  if (health.app === "down" || health.db === "down" || health.externalAiProvider === "down") {
    return "Bitte Incident-Playbook und NIS2-Meldewege prüfen. Monitoring, Eskalation und Nachweise zur Erreichbarkeit absichern.";
  }
  if (health.db !== "up" || health.externalAiProvider !== "up") {
    return "Monitoring und Incident Readiness prüfen — KI-Provider oder Datenbank zeigen Einschränkungen (Continuous Monitoring / NIS2-Betrieb).";
  }
  return null;
}
