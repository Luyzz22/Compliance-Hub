const DIRECTIVE_PATTERN = /^[a-z][a-z0-9-]{0,79}$/;
const ALLOWED_DISPOSITIONS = new Set(["enforce", "report"]);

export const CSP_REPORT_MAX_BYTES = 16 * 1024;
export const CSP_REPORT_MAX_ITEMS = 10;

export type SanitizedCspViolation = {
  event: "csp_violation";
  disposition: "enforce" | "report" | "unknown";
  effective_directive: string;
  document_origin: string;
  blocked_resource: string;
  source_origin: string | null;
  status_code: number | null;
};

function objectRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function firstString(record: Record<string, unknown>, keys: string[]): string {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return "";
}

function sanitizedDirective(record: Record<string, unknown>): string {
  const raw = firstString(record, [
    "effectiveDirective",
    "effective-directive",
    "violatedDirective",
    "violated-directive",
  ]).toLowerCase();
  const directive = raw.split(/\s+/, 1)[0];
  return DIRECTIVE_PATTERN.test(directive) ? directive : "unknown";
}

function sanitizedOrigin(value: string): string {
  if (!value) return "unknown";
  const normalized = value.toLowerCase();
  if (normalized === "inline" || normalized === "eval" || normalized === "self") {
    return normalized;
  }
  if (normalized.startsWith("data:")) return "data:";
  if (normalized.startsWith("blob:")) return "blob:";
  try {
    const url = new URL(value);
    if (url.protocol === "https:" || url.protocol === "http:") return url.origin;
  } catch {
    // Attacker-controlled report fields intentionally collapse to a fixed label.
  }
  return "other";
}

function sanitizedStatusCode(record: Record<string, unknown>): number | null {
  const value = record.statusCode ?? record["status-code"];
  return typeof value === "number" && Number.isInteger(value) && value >= 100 && value <= 599
    ? value
    : null;
}

function sanitizeBody(record: Record<string, unknown>): SanitizedCspViolation {
  const dispositionRaw = firstString(record, ["disposition"]).toLowerCase();
  const disposition = ALLOWED_DISPOSITIONS.has(dispositionRaw)
    ? (dispositionRaw as "enforce" | "report")
    : "unknown";

  return {
    event: "csp_violation",
    disposition,
    effective_directive: sanitizedDirective(record),
    document_origin: sanitizedOrigin(
      firstString(record, ["documentURL", "document-uri", "url"]),
    ),
    blocked_resource: sanitizedOrigin(
      firstString(record, ["blockedURL", "blocked-uri"]),
    ),
    source_origin: (() => {
      const source = firstString(record, ["sourceFile", "source-file"]);
      return source ? sanitizedOrigin(source) : null;
    })(),
    status_code: sanitizedStatusCode(record),
  };
}

export function sanitizeCspReports(payload: unknown): SanitizedCspViolation[] {
  const candidates: Record<string, unknown>[] = [];

  const legacy = objectRecord(payload);
  const legacyBody = legacy ? objectRecord(legacy["csp-report"]) : null;
  if (legacyBody) candidates.push(legacyBody);

  if (Array.isArray(payload)) {
    for (const item of payload.slice(0, CSP_REPORT_MAX_ITEMS)) {
      const report = objectRecord(item);
      if (!report || report.type !== "csp-violation") continue;
      const body = objectRecord(report.body);
      if (body) candidates.push(body);
    }
  }

  return candidates.slice(0, CSP_REPORT_MAX_ITEMS).map(sanitizeBody);
}
