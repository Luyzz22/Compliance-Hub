#!/usr/bin/env node
/**
 * Wave 32 – GTM Alert-Check für Cron / GitHub Actions / n8n HTTP-Request.
 *
 * Env:
 *   COMPLIANCEHUB_BASE_URL  z. B. https://app.example.com (ohne Slash am Ende)
 *   LEAD_ADMIN_SECRET oder GTM_ALERT_SECRET (Query ?secret=)
 *
 * Exit 0 immer, wenn HTTP OK; stderr bei Fehler.
 */

const base = (process.env.COMPLIANCEHUB_BASE_URL || "http://localhost:3000").replace(/\/$/, "");
const secret = (process.env.GTM_ALERT_SECRET || process.env.LEAD_ADMIN_SECRET || "").trim();
if (!secret) {
  console.error("gtm-alert-check: set LEAD_ADMIN_SECRET or GTM_ALERT_SECRET");
  process.exit(1);
}

const url = `${base}/api/admin/gtm/alert-check?secret=${encodeURIComponent(secret)}`;

const res = await fetch(url, { method: "GET" });
const text = await res.text();
let json;
try {
  json = JSON.parse(text);
} catch {
  console.error("gtm-alert-check: non-JSON response", res.status, text.slice(0, 500));
  process.exit(1);
}

if (!res.ok) {
  console.error("gtm-alert-check: HTTP", res.status, json);
  process.exit(1);
}

console.log(JSON.stringify({ ok: json.ok, fired: json.fired, counts: json.counts }, null, 2));
if (json.summary_de) console.log(json.summary_de);
if (json.fired && json.findings?.length) {
  process.exitCode = 2;
}
