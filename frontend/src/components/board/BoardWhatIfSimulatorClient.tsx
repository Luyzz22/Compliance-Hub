"use client";

import Link from "next/link";
import React, { useMemo, useState } from "react";

import {
  fetchTenantAISystems,
  postWhatIfBoardImpact,
  type WhatIfScenarioResultPayload,
  type AISystem,
} from "@/lib/api";
import { CH_BTN_PRIMARY, CH_BTN_SECONDARY } from "@/lib/boardLayout";
import { featureWhatIfSimulator } from "@/lib/config";

function isHighRisk(s: AISystem): boolean {
  const r = s.risk_level ?? s.risklevel;
  return r === "high";
}

function formatRatio(x: number): string {
  return `${Math.round(x * 100)}%`;
}

export function BoardWhatIfSimulatorClient() {
  const enabled = featureWhatIfSimulator();
  const [systems, setSystems] = useState<AISystem[] | null>(null);
  const [pick, setPick] = useState<string[]>([]);
  const [incident, setIncident] = useState<Record<string, string>>({});
  const [supplier, setSupplier] = useState<Record<string, string>>({});
  const [euAct, setEuAct] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [result, setResult] = useState<WhatIfScenarioResultPayload | null>(null);

  const highRisk = useMemo(
    () => (systems ?? []).filter(isHighRisk),
    [systems]
  );

  React.useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    void (async () => {
      try {
        const list = await fetchTenantAISystems();
        if (!cancelled) setSystems(list);
      } catch {
        if (!cancelled) setSystems([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [enabled]);

  if (!enabled) return null;

  const toggleSystem = (id: string) => {
    setPick((prev) => {
      if (prev.includes(id)) {
        return prev.filter((x) => x !== id);
      }
      if (prev.length >= 3) return prev;
      return [...prev, id];
    });
  };

  const runSim = async () => {
    setBusy(true);
    setErr(null);
    setResult(null);
    const kpi_adjustments: {
      ai_system_id: string;
      kpi_type: "INCIDENT_RESPONSE_MATURITY" | "SUPPLIER_RISK_COVERAGE" | "EU_AI_ACT_CONTROL_FULFILLMENT";
      target_value_percent: number;
    }[] = [];
    const parsePct = (raw: string | undefined): number | null => {
      if (raw === undefined || raw.trim() === "") return null;
      const n = Number(raw);
      if (!Number.isFinite(n)) return null;
      return Math.min(100, Math.max(0, Math.round(n)));
    };
    for (const id of pick) {
      const i = parsePct(incident[id]);
      const sup = parsePct(supplier[id]);
      const eu = parsePct(euAct[id]);
      if (i !== null) {
        kpi_adjustments.push({
          ai_system_id: id,
          kpi_type: "INCIDENT_RESPONSE_MATURITY",
          target_value_percent: i,
        });
      }
      if (sup !== null) {
        kpi_adjustments.push({
          ai_system_id: id,
          kpi_type: "SUPPLIER_RISK_COVERAGE",
          target_value_percent: sup,
        });
      }
      if (eu !== null) {
        kpi_adjustments.push({
          ai_system_id: id,
          kpi_type: "EU_AI_ACT_CONTROL_FULFILLMENT",
          target_value_percent: eu,
        });
      }
    }
    try {
      const out = await postWhatIfBoardImpact({ kpi_adjustments });
      setResult(out);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Simulation fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section
      className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
      aria-label="What-if-Simulator"
      data-testid="board-what-if-panel"
    >
      <h2 className="text-base font-semibold text-slate-900">What-if-Simulator</h2>
      <p className="mt-1 text-xs text-slate-600">
        Nur Simulation – es werden keine produktiven KPI- oder Compliance-Daten geändert. Dient
        CISO/Board zur Szenenplanung (NIS2-/KRITIS-KPI-Zielwerte und optional EU-AI-Act-Kontrollgrad
        je System).
      </p>

      {highRisk.length === 0 ? (
        <p className="mt-3 text-sm text-slate-500">
          Keine High-Risk-KI-Systeme im Register – Simulation ist eingeschränkt sinnvoll.
        </p>
      ) : (
        <>
          <div className="mt-4">
            <p className="text-xs font-medium text-slate-600">High-Risk-Systeme (max. 3)</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {highRisk.map((s) => {
                const on = pick.includes(s.id);
                return (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => toggleSystem(s.id)}
                    className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 transition ${
                      on
                        ? "bg-cyan-600 text-white ring-cyan-700"
                        : "bg-slate-50 text-slate-700 ring-slate-200 hover:bg-slate-100"
                    }`}
                  >
                    {s.name}
                  </button>
                );
              })}
            </div>
          </div>

          {pick.length > 0 ? (
            <div className="mt-4 space-y-4">
              {pick.map((id) => {
                const s = highRisk.find((x) => x.id === id);
                if (!s) return null;
                return (
                  <div
                    key={id}
                    className="rounded-xl border border-slate-100 bg-slate-50/60 p-3 text-sm"
                  >
                    <p className="font-semibold text-slate-900">{s.name}</p>
                    <div className="mt-2 grid gap-3 sm:grid-cols-3">
                      <label className="block text-xs text-slate-600">
                        Incident-Readiness %
                        <input
                          type="number"
                          min={0}
                          max={100}
                          className="mt-1 w-full rounded-lg border border-slate-200 px-2 py-1"
                          value={incident[id] ?? ""}
                          placeholder="—"
                          onChange={(e) =>
                            setIncident((m) => ({ ...m, [id]: e.target.value }))
                          }
                        />
                      </label>
                      <label className="block text-xs text-slate-600">
                        Supplier-Coverage %
                        <input
                          type="number"
                          min={0}
                          max={100}
                          className="mt-1 w-full rounded-lg border border-slate-200 px-2 py-1"
                          value={supplier[id] ?? ""}
                          placeholder="—"
                          onChange={(e) =>
                            setSupplier((m) => ({ ...m, [id]: e.target.value }))
                          }
                        />
                      </label>
                      <label className="block text-xs text-slate-600">
                        EU-AI-Act-Kontrollgrad % (simuliert)
                        <input
                          type="number"
                          min={0}
                          max={100}
                          className="mt-1 w-full rounded-lg border border-slate-200 px-2 py-1"
                          value={euAct[id] ?? ""}
                          placeholder="—"
                          onChange={(e) => setEuAct((m) => ({ ...m, [id]: e.target.value }))}
                        />
                      </label>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : null}

          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              className={CH_BTN_PRIMARY}
              disabled={busy || pick.length === 0}
              onClick={() => void runSim()}
            >
              {busy ? "Berechne…" : "Simulation berechnen"}
            </button>
            <Link
              href="/board/eu-ai-act-readiness"
              className={`${CH_BTN_SECONDARY} inline-flex items-center`}
            >
              Maßnahmen / Action-Drafts
            </Link>
          </div>
        </>
      )}

      {err ? (
        <p className="mt-3 text-sm text-rose-700" role="alert">
          {err}
        </p>
      ) : null}

      {result ? (
        <div className="mt-4 rounded-xl border border-emerald-100 bg-emerald-50/50 p-4 text-sm text-slate-800">
          <p className="font-semibold text-emerald-950">Ergebnis</p>
          <ul className="mt-2 list-inside list-disc space-y-1">
            <li>
              Readiness: {formatRatio(result.original_readiness)} →{" "}
              {formatRatio(result.simulated_readiness)}
            </li>
            <li>
              NIS2-KPI-Mittel (Board):{" "}
              {result.original_board_kpis.nis2_kritis_kpi_mean_percent ?? "–"} % →{" "}
              {result.simulated_board_kpis.nis2_kritis_kpi_mean_percent ?? "–"} %
            </li>
            <li>
              Alerts: {result.original_alerts_count} → {result.simulated_alerts_count}
            </li>
          </ul>
          {result.alert_signatures_resolved.length > 0 ? (
            <p className="mt-2 text-xs text-slate-600">
              Entfallene Alerts: {result.alert_signatures_resolved.join(", ")}
            </p>
          ) : null}
          {result.alert_signatures_new.length > 0 ? (
            <p className="mt-2 text-xs text-slate-600">
              Neue Alerts: {result.alert_signatures_new.join(", ")}
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
