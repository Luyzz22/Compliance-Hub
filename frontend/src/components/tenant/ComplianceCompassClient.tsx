"use client";

import { useCallback, useEffect, useState } from "react";

import { fetchComplianceCompass, type ComplianceCompassSnapshot } from "@/lib/complianceCompassApi";

const SF = "ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', sans-serif";

function postureLabel(p: string): { de: string; chip: string } {
  const m: Record<string, { de: string; chip: string }> = {
    strong: { de: "Robust", chip: "bg-emerald-500/15 text-emerald-800 ring-1 ring-emerald-500/20" },
    steady: { de: "Stabil", chip: "bg-sky-500/10 text-sky-900 ring-1 ring-sky-500/15" },
    watch: { de: "Beobachten", chip: "bg-amber-500/12 text-amber-900 ring-1 ring-amber-500/20" },
    elevated: { de: "Erhöhtes Tempo", chip: "bg-rose-500/10 text-rose-900 ring-1 ring-rose-500/20" },
  };
  return m[p] ?? { de: p, chip: "bg-slate-200/60 text-slate-800" };
}

function FusionRing({ value, size = 200 }: { value: number; size?: number }) {
  const r = 42;
  const vb = 100;
  const cx = vb / 2;
  const c = 2 * Math.PI * r;
  const p = Math.max(0, Math.min(1, value / 100));
  const dash = c * p;
  const off = c - dash;
  const stroke = 7;
  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${vb} ${vb}`}
      className="shrink-0 drop-shadow-sm"
      aria-hidden
    >
      <defs>
        <linearGradient id="cc-ring" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#0ea5e9" stopOpacity="0.95" />
          <stop offset="55%" stopColor="#6366f1" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#22c55e" stopOpacity="0.95" />
        </linearGradient>
      </defs>
      <circle
        cx={cx}
        cy={cx}
        r={r}
        fill="none"
        stroke="rgba(15,23,42,0.08)"
        strokeWidth={stroke}
      />
      <circle
        cx={cx}
        cy={cx}
        r={r}
        fill="none"
        stroke="url(#cc-ring)"
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeDasharray={c}
        strokeDashoffset={off}
        transform={`rotate(-90 ${cx} ${cx})`}
        className="transition-all duration-700 ease-out"
      />
    </svg>
  );
}

type Props = { tenantId: string };

export function ComplianceCompassClient({ tenantId }: Props) {
  const [data, setData] = useState<ComplianceCompassSnapshot | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      setData(await fetchComplianceCompass(tenantId));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Laden fehlgeschlagen");
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    void load();
  }, [load]);

  const pMeta = data ? postureLabel(data.posture) : null;

  return (
    <div
      className="min-h-[calc(100vh-8rem)] -mx-4 -mt-2 rounded-[2rem] bg-gradient-to-b from-slate-50 via-white to-slate-100/80 px-4 py-8 sm:px-8"
      style={{ fontFamily: SF }}
    >
      {err ? (
        <div
          className="rounded-2xl border border-rose-200/60 bg-rose-50/80 px-4 py-3 text-sm text-rose-900"
          role="status"
        >
          {err}
        </div>
      ) : null}

      {loading && !data ? (
        <div className="flex h-64 items-center justify-center text-slate-400">Laden…</div>
      ) : null}

      {data && (
        <div className="mx-auto max-w-5xl space-y-10">
          <header className="text-center sm:text-left">
            <p className="text-xs font-medium uppercase tracking-[0.2em] text-slate-400">Compliance Compass</p>
            <h1
              className="mt-2 text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl"
            >
              Fusions-Intelligence
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-500 sm:text-base">
              Ein klarer Nordstern-Index aus Reife, Ausführung, Kadenz und Lagebild
              (deterministisch, mandantisoliert, ohne LLM im API-Kern).
            </p>
          </header>

          <section
            className="relative overflow-hidden rounded-[1.75rem] border border-white/70 bg-white/60 p-6 shadow-[0_24px_80px_rgba(15,23,42,0.06)] backdrop-blur-2xl sm:p-9"
          >
            <div className="flex flex-col items-center gap-8 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex flex-col items-center gap-1 sm:items-start">
                <p className="text-[11px] font-medium uppercase tracking-widest text-slate-400">
                  Fusions-Index
                </p>
                <div className="relative">
                  <FusionRing value={data.fusion_index_0_100} size={220} />
                  <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
                    <span
                      className="text-5xl font-extralight tabular-nums tracking-tight text-slate-900"
                      style={{ fontFeatureSettings: '"tnum" 1' }}
                    >
                      {data.fusion_index_0_100}
                    </span>
                    <span className="text-[0.7rem] font-medium uppercase tracking-[0.18em] text-slate-500">
                      von 100
                    </span>
                  </div>
                </div>
              </div>
              <div className="max-w-xl space-y-4 text-center sm:text-left">
                <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
                  {pMeta ? (
                    <span
                      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${pMeta.chip}`}
                    >
                      {pMeta.de}
                    </span>
                  ) : null}
                  <span className="text-xs text-slate-500">
                    Modell {data.model_version} · Vertrauen in Daten: {data.confidence_0_100}
                  </span>
                </div>
                <p className="text-base font-normal leading-7 text-slate-800">{data.narrative_de}</p>
                <button
                  type="button"
                  onClick={() => void load()}
                  className="rounded-full border border-slate-200/80 bg-white/80 px-4 py-1.5 text-sm font-medium text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-white"
                >
                  Aktualisieren
                </button>
              </div>
            </div>
          </section>

          <section>
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Säulen</h2>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              {data.pillars.map((p) => (
                <div
                  key={p.key}
                  className="group rounded-2xl border border-white/80 bg-gradient-to-b from-white/90 to-slate-50/80 p-5 shadow-[0_12px_40px_rgba(15,23,42,0.04)] backdrop-blur"
                >
                  <div className="flex items-baseline justify-between gap-2">
                    <h3 className="text-sm font-medium text-slate-900">{p.label_de}</h3>
                    <span className="text-2xl font-light tabular-nums text-slate-800">{p.score_0_100}</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">Gewicht: {Math.round(p.weight_in_fusion * 100)} %</p>
                  <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-slate-200/60">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-sky-500 via-indigo-500 to-emerald-500 transition-all duration-500"
                      style={{ width: `${p.score_0_100}%` }}
                    />
                  </div>
                  <p className="mt-3 text-sm leading-relaxed text-slate-600">{p.detail_de}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-slate-200/60 bg-white/50 p-5 text-sm text-slate-600 shadow-sm backdrop-blur">
              <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400">Datenhoheit</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-700">{data.privacy_de}</p>
            </div>
            <div className="rounded-2xl border border-slate-200/60 bg-slate-900/90 p-5 text-sm text-slate-100 shadow-lg backdrop-blur">
              <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-300">Provenance (API)</h3>
              <ul className="mt-2 space-y-1 font-mono text-[0.7rem] leading-5 text-slate-200">
                <li>readiness: {data.provenance.readiness_score} ({data.provenance.readiness_level})</li>
                <li>open/in_progress/escal: {data.provenance.workflow_open_or_active}</li>
                <li>overdue: {data.provenance.workflow_overdue} · escalated: {data.provenance.workflow_escalated}</li>
                <li>events 24h: {data.provenance.workflow_events_24h}</li>
                {data.provenance.rule_bundle_version_last_run ? (
                  <li>last bundle: {data.provenance.rule_bundle_version_last_run}</li>
                ) : null}
              </ul>
              <p className="mt-3 text-xs leading-5 text-slate-400">{data.provenance.explainability_de}</p>
            </div>
          </section>

          <p className="text-center text-[0.7rem] text-slate-400 sm:text-left">
            Stand: {new Date(data.as_of_utc).toLocaleString("de-DE", { timeZone: "UTC" })} UTC ·
            tenant <span className="font-mono text-slate-500">{data.tenant_id}</span>
          </p>
        </div>
      )}
    </div>
  );
}
