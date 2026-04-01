"use client";

import React, { useState } from "react";

const tabs = [
  {
    id: "ai",
    label: "EU AI Act, ISO 42001",
    title: "AI-Governance ohne Excel-Chaos.",
    body: "KI-System-Register, Risikoklassifizierung und Technical File in einer gemeinsamen Oberfläche – zur Dokumentation und zum Review, abhängig von Ihrem Einsatzszenario.",
  },
  {
    id: "nis2",
    label: "NIS2 & ISO 27001",
    title: "Resilienz und Lieferkette im Blick.",
    body: "Incident-Readiness, Supplier-Risk und OT/IT-Segregation – anschlussfähig an Ihre GRC-Landschaft.",
  },
  {
    id: "berater",
    label: "Berater-first",
    title: "Skalierbare Mandantenprojekte.",
    body: "Exportfähige Reports, Evidence-Pfade und Board-Ansichten für Kanzlei und Enterprise (DATEV-taugliche Strukturen projektabhängig, keine Produktzertifizierung).",
  },
] as const;

export function HomeProductPreview() {
  const [active, setActive] = useState(0);
  const t = tabs[active];

  return (
    <div
      className="rounded-2xl border border-slate-200/90 bg-gradient-to-br from-white via-slate-50/90 to-cyan-50/50 p-4 shadow-lg shadow-slate-200/60 ring-1 ring-slate-100 sm:p-5"
      role="region"
      aria-label="Produktvorschau"
    >
      <div className="flex justify-between text-xs text-slate-500">
        <span className="font-medium text-slate-700">Musterindustrie Demo GmbH</span>
        <span className="font-semibold text-cyan-700">Policy Engine</span>
      </div>

      <div className="mt-4 grid gap-3">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {[
            { k: "EU AI Act", on: true },
            { k: "ISO 42001", on: false },
            { k: "ISO 27001", on: false },
            { k: "NIS2", on: false },
          ].map((x) => (
            <div
              key={x.k}
              className={`rounded-xl border px-2 py-2 text-center text-[0.65rem] font-semibold sm:text-[0.7rem] ${
                x.on
                  ? "border-cyan-200 bg-gradient-to-br from-cyan-50 to-white text-slate-800 shadow-sm"
                  : "border-slate-200/80 bg-white/80 text-slate-500"
              }`}
            >
              <div className="mb-1.5">{x.k}</div>
              <div
                className={`mx-auto h-1 max-w-[4rem] rounded-full ${
                  x.on
                    ? "bg-gradient-to-r from-cyan-500 to-emerald-500"
                    : "bg-slate-200"
                }`}
              />
            </div>
          ))}
        </div>

        <div className="rounded-xl border border-slate-200/90 bg-white p-3 shadow-inner sm:p-4">
          <div
            className="mb-3 flex flex-wrap gap-2"
            role="tablist"
            aria-label="Anwendungsfälle"
          >
            {tabs.map((tab, i) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={i === active}
                onClick={() => setActive(i)}
                className={`rounded-full border px-3 py-1.5 text-[0.65rem] font-semibold transition sm:text-xs ${
                  i === active
                    ? "border-transparent bg-gradient-to-r from-cyan-600 to-emerald-600 text-white shadow-sm"
                    : "border-slate-200 bg-slate-50/80 text-slate-600 hover:border-slate-300 hover:bg-white"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <div role="tabpanel">
            <h3 className="text-sm font-semibold text-slate-900 sm:text-base">{t.title}</h3>
            <p className="mt-1 text-xs leading-relaxed text-slate-600 sm:text-[0.8rem]">
              {t.body}
            </p>
            <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-3">
              <div className="flex items-center justify-between gap-2 rounded-full border border-slate-200 bg-slate-50/80 px-3 py-2 text-[0.65rem] sm:text-xs">
                <span className="text-slate-500">Controls compliant</span>
                <span className="font-semibold tabular-nums text-slate-900">214 / 238</span>
              </div>
              <div className="flex items-center justify-between gap-2 rounded-full border border-slate-200 bg-slate-50/80 px-3 py-2 text-[0.65rem] sm:text-xs">
                <span className="text-slate-500">Offene Violations</span>
                <span className="font-semibold tabular-nums text-amber-700">9</span>
              </div>
              <div className="flex items-center justify-between gap-2 rounded-full border border-slate-200 bg-slate-50/80 px-3 py-2 text-[0.65rem] sm:text-xs">
                <span className="text-slate-500">Board-Readiness</span>
                <span className="font-semibold text-slate-800">in 2 Tagen</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {[
          { l: "KI-Systeme im Register", v: "27" },
          { l: "Offene Violations", v: "9", warn: true },
          { l: "NIS2-Risiken high+", v: "5" },
          { l: "Evidence Coverage", v: "91 %" },
        ].map((x) => (
          <div
            key={x.l}
            className="rounded-xl border border-slate-200/80 bg-white px-2 py-2.5 text-center shadow-sm"
          >
            <div className="text-[0.6rem] font-medium uppercase tracking-wide text-slate-500 sm:text-[0.65rem]">
              {x.l}
            </div>
            <div
              className={`mt-1 text-sm font-semibold tabular-nums sm:text-base ${
                x.warn ? "text-amber-700" : "text-slate-900"
              }`}
            >
              {x.v}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
