"use client";

import { useCallback, useEffect, useState } from "react";

import {
  fetchDemoTenantTemplates,
  postDemoTenantSeed,
  type DemoSeedResponseDto,
  type DemoTenantTemplateDto,
} from "@/lib/api";
import { CH_BTN_PRIMARY, CH_BTN_SECONDARY, CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";
import { openWorkspaceTenantAndGoComplianceOverview } from "@/lib/workspaceTenantClient";

export interface DemoTenantSetupPanelProps {
  /** Wenn gesetzt, wird nach erfolgreichem Seed advisor_tenants verknüpft. */
  advisorId?: string;
  /** Vorschlag für das Ziel-Mandantenfeld. */
  defaultTenantId?: string;
}

export function DemoTenantSetupPanel({
  advisorId,
  defaultTenantId = "",
}: DemoTenantSetupPanelProps) {
  const [templates, setTemplates] = useState<DemoTenantTemplateDto[]>([]);
  const [templateKey, setTemplateKey] = useState("");
  const [tenantId, setTenantId] = useState(defaultTenantId);
  const [linkAdvisor, setLinkAdvisor] = useState(!!advisorId?.trim());
  const [loadingList, setLoadingList] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [seedError, setSeedError] = useState<string | null>(null);
  const [result, setResult] = useState<DemoSeedResponseDto | null>(null);
  const [templateLoadAttempt, setTemplateLoadAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoadingList(true);
      setListError(null);
      try {
        const list = await fetchDemoTenantTemplates();
        if (!cancelled) {
          setTemplates(list);
          if (list.length > 0) setTemplateKey(list[0].key);
        }
      } catch (e) {
        if (!cancelled) {
          const detail = e instanceof Error && e.message ? ` ${e.message}` : "";
          setListError(
            `Szenario-Templates konnten nicht geladen werden.${detail} Bitte COMPLIANCEHUB_DEMO_SEED_API_KEY, Feature-Flag demo_seeding und Netzwerk prüfen, dann erneut versuchen.`,
          );
        }
      } finally {
        if (!cancelled) setLoadingList(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [templateLoadAttempt]);

  const runSeed = useCallback(async () => {
    setSeedError(null);
    setResult(null);
    const tid = tenantId.trim();
    if (!tid || !templateKey) {
      setSeedError("Bitte Template und Mandanten-ID angeben.");
      return;
    }
    setSeeding(true);
    try {
      const res = await postDemoTenantSeed({
        template_key: templateKey,
        tenant_id: tid,
        advisor_id:
          linkAdvisor && advisorId?.trim() ? advisorId.trim() : undefined,
      });
      setResult(res);
    } catch (e) {
      const base = e instanceof Error ? e.message : "Demo-Seed fehlgeschlagen.";
      setError(
        `${base} Bitte Eingaben prüfen und erneut auf «Demo-Daten einspielen» klicken; bei anhaltendem Fehler Server-Logs prüfen.`,
      );
    } finally {
      setSeeding(false);
    }
  }, [tenantId, templateKey, linkAdvisor, advisorId]);

  return (
    <section className={CH_CARD} aria-label="Demo-Mandanten">
      <p className={CH_SECTION_LABEL}>Demo-Tenants (Pilot / intern)</p>
      <p className="mt-1 text-sm text-slate-600">
        Nur für Mandanten-IDs in{" "}
        <code className="rounded bg-slate-100 px-1 text-xs">COMPLIANCEHUB_DEMO_SEED_TENANT_IDS</code>{" "}
        und mit separatem Demo-Seed-Key. Anschließend Guided Setup, Boards und Advisor-Report
        nutzen.
      </p>

      {listError ? (
        <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-900">
          <p>{listError}</p>
          {loadingList ? null : (
            <button
              type="button"
              className="mt-2 text-xs font-semibold text-rose-800 underline"
              onClick={() => setTemplateLoadAttempt((n) => n + 1)}
            >
              Template-Liste erneut laden
            </button>
          )}
        </div>
      ) : null}

      {seedError ? (
        <p className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-900">
          {seedError}
        </p>
      ) : null}

      {result ? (
        <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-3 text-sm text-emerald-950">
          <p className="font-semibold">Demo-Setup abgeschlossen</p>
          <ul className="mt-2 list-inside list-disc text-emerald-900">
            <li>{result.ai_systems_count} KI-Systeme</li>
            <li>{result.governance_actions_count} Governance-Actions</li>
            <li>{result.evidence_files_count} Evidenzen</li>
            <li>{result.nis2_kpi_rows_count} NIS2-KPI-Zeilen</li>
            <li>{result.policy_rows_count} Policy-Zeilen</li>
          </ul>
          <p className="mt-2 text-xs text-emerald-800">
            Alerts und Readiness sind aktiv. Öffnen Sie den Mandanten im Workspace für die
            Compliance-Übersicht.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              className={`${CH_BTN_PRIMARY} text-xs`}
              onClick={() => openWorkspaceTenantAndGoComplianceOverview(result.tenant_id)}
            >
              Compliance-Übersicht öffnen
            </button>
          </div>
        </div>
      ) : null}

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div>
          <label className="block text-xs font-semibold text-slate-600" htmlFor="demo-template">
            Szenario-Template
          </label>
          <select
            id="demo-template"
            className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
            disabled={loadingList || templates.length === 0}
            value={templateKey}
            onChange={(e) => setTemplateKey(e.target.value)}
          >
            {templates.map((t) => (
              <option key={t.key} value={t.key}>
                {t.name}
              </option>
            ))}
          </select>
          {templates.find((t) => t.key === templateKey) ? (
            <p className="mt-2 text-xs text-slate-500">
              {templates.find((t) => t.key === templateKey)?.description}
            </p>
          ) : null}
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-600" htmlFor="demo-tenant-id">
            Ziel-Mandanten-ID
          </label>
          <input
            id="demo-tenant-id"
            className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 font-mono text-sm"
            placeholder="z. B. demo-pilot-001"
            value={tenantId}
            onChange={(e) => setTenantId(e.target.value)}
          />
        </div>
      </div>

      {advisorId?.trim() ? (
        <label className="mt-3 flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={linkAdvisor}
            onChange={(e) => setLinkAdvisor(e.target.checked)}
          />
          Mandant mit diesem Berater verknüpfen (advisor_tenants)
        </label>
      ) : null}

      <div className="mt-4">
        <button
          type="button"
          disabled={seeding || loadingList}
          className={`${CH_BTN_SECONDARY} text-sm disabled:opacity-50`}
          onClick={() => void runSeed()}
        >
          {seeding ? "Spiele Demo-Daten ein…" : "Demo-Daten einspielen"}
        </button>
      </div>
    </section>
  );
}
