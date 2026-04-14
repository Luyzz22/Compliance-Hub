"use client";

import React, { useState } from "react";
import Link from "next/link";
import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";

import {
  CH_BTN_PRIMARY,
  CH_CARD,
  CH_PAGE_NAV_LINK,
  CH_SECTION_LABEL,
} from "@/lib/boardLayout";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.COMPLIANCEHUB_API_BASE_URL ||
  "http://localhost:8000";
const API_KEY =
  process.env.NEXT_PUBLIC_API_KEY ||
  process.env.COMPLIANCEHUB_API_KEY ||
  "tenant-overview-key";
const TENANT_ID =
  process.env.NEXT_PUBLIC_TENANT_ID ||
  process.env.COMPLIANCEHUB_TENANT_ID ||
  "tenant-overview-001";

export default function DatevExportPage() {
  const today = new Date().toISOString().slice(0, 10);
  const firstOfMonth = today.slice(0, 8) + "01";

  const [periodFrom, setPeriodFrom] = useState(firstOfMonth);
  const [periodTo, setPeriodTo] = useState(today);
  const [skr, setSkr] = useState<"SKR03" | "SKR04">("SKR03");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    checksum: string;
    lines: number;
  } | null>(null);

  async function handleExport() {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const params = new URLSearchParams({
        period_from: periodFrom,
        period_to: periodTo,
        skr,
      });
      const opaRole = process.env.NEXT_PUBLIC_OPA_USER_ROLE?.trim();
      const headers: Record<string, string> = {
        "x-api-key": API_KEY,
        "x-tenant-id": TENANT_ID,
      };
      if (opaRole) headers["x-opa-user-role"] = opaRole;

      const res = await fetch(
        `${API_BASE_URL}/api/v1/enterprise/datev/export?${params}`,
        { method: "POST", headers },
      );

      if (res.status === 403) {
        setError(
          "Zugriff verweigert — DATEV-Export erfordert TENANT_ADMIN oder COMPLIANCE_ADMIN Rolle.",
        );
        return;
      }
      if (!res.ok) {
        const body = await res.text();
        setError(`Export fehlgeschlagen (HTTP ${res.status}): ${body}`);
        return;
      }

      const content = await res.text();
      const checksum = res.headers.get("X-Checksum-SHA256") ?? "–";
      const lines = content.trim().split("\r\n").length;

      // Trigger download
      const blob = new Blob([content], {
        type: "text/plain;charset=windows-1252",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `EXTF_export_${periodFrom}_${periodTo}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      setResult({ checksum, lines });
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Unbekannter Fehler beim Export.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-w-0">
      <EnterprisePageHeader
        eyebrow="Reporting"
        title="DATEV Export (EXTF)"
        description="GoBD-konformer DATEV-ASCII-Export (EXTF-Standard) für Bußgelder, GRC-Beraterhonorare, Zertifizierungskosten und Cyber-Versicherungsprämien."
        below={
          <>
            <Link href="/board/executive-dashboard" className={CH_PAGE_NAV_LINK}>
              Executive Dashboard
            </Link>
            <Link href="/board/gap-analysis" className={CH_PAGE_NAV_LINK}>
              Gap-Analyse
            </Link>
          </>
        }
      />

      {/* ── Export Config ── */}
      <section className={`${CH_CARD} mb-6 space-y-4`}>
        <p className={CH_SECTION_LABEL}>Export-Parameter</p>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
            Zeitraum von
            <input
              type="date"
              value={periodFrom}
              onChange={(e) => setPeriodFrom(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
            Zeitraum bis
            <input
              type="date"
              value={periodTo}
              onChange={(e) => setPeriodTo(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
            Kontenrahmen
            <select
              value={skr}
              onChange={(e) => setSkr(e.target.value as "SKR03" | "SKR04")}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="SKR03">SKR03</option>
              <option value="SKR04">SKR04</option>
            </select>
          </label>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleExport}
            disabled={loading}
            className={CH_BTN_PRIMARY}
          >
            {loading ? "Exportiere…" : "EXTF-Export starten"}
          </button>
          <span className="text-xs text-slate-400">
            Nur für TENANT_ADMIN / COMPLIANCE_ADMIN (MFA Step-up empfohlen)
          </span>
        </div>
      </section>

      {/* ── Error ── */}
      {error && (
        <div className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900">
          {error}
        </div>
      )}

      {/* ── Result ── */}
      {result && (
        <section className={`${CH_CARD} space-y-2`}>
          <p className={CH_SECTION_LABEL}>Export erfolgreich</p>
          <p className="text-sm text-slate-700">
            <strong>Zeilen:</strong> {result.lines} (Header + Datensätze)
          </p>
          <p className="text-sm text-slate-700">
            <strong>Prüfsumme (SHA-256):</strong>{" "}
            <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">
              {result.checksum}
            </code>
          </p>
          <p className="text-xs text-slate-400">
            Datei wurde automatisch heruntergeladen. Bitte in DATEV importieren
            und mit der Prüfsumme verifizieren.
          </p>
        </section>
      )}

      {/* ── Info Box ── */}
      <section className={`${CH_CARD} mt-6 space-y-2`}>
        <p className={CH_SECTION_LABEL}>Hinweise</p>
        <ul className="list-inside list-disc space-y-1 text-sm text-slate-600">
          <li>
            Format: DATEV EXTF ASCII (Formatversion 510, Buchungsstapel)
          </li>
          <li>
            Buchungstypen: Bußgelder (BSI/Datenschutz), GRC-Beraterhonorare,
            Zertifizierungskosten (ISO 27001, ISO 42001), Versicherungsprämien
          </li>
          <li>Kontenrahmen: SKR03 oder SKR04 wählbar</li>
          <li>
            Prüfsumme (SHA-256) wird vor Export berechnet und im HTTP-Header
            mitgeliefert
          </li>
          <li>
            Alle Exports werden im Audit-Log protokolliert (GoBD-konform)
          </li>
        </ul>
      </section>
    </div>
  );
}
