"use client";

import React, { useEffect, useState } from "react";

const slides = [
  {
    id: "kpis",
    label: "Board KPIs",
    icon: "📊",
    content: (
      <div className="flex h-full flex-col p-6">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Executive KPIs
        </div>
        <div className="mt-4 grid grid-cols-3 gap-2">
          {[
            { v: "78%", l: "ISO 42001" },
            { v: "64%", l: "NIS2 Inc." },
            { v: "82%", l: "Supplier" },
          ].map((k) => (
            <div
              key={k.l}
              className="rounded-xl border border-slate-200/80 bg-white/90 p-3 shadow-sm"
            >
              <div className="text-lg font-semibold tabular-nums text-slate-900">{k.v}</div>
              <div className="text-[0.65rem] font-medium text-slate-500">{k.l}</div>
            </div>
          ))}
        </div>
        <ul className="mt-5 space-y-2 text-left text-sm leading-snug text-slate-600">
          <li className="flex gap-2">
            <span className="shrink-0 text-cyan-600">·</span>
            Executive Overview für Vorstand &amp; Aufsicht
          </li>
          <li className="flex gap-2">
            <span className="shrink-0 text-cyan-600">·</span>
            Alerts &amp; Eskalationspfade auf einen Blick
          </li>
          <li className="flex gap-2">
            <span className="shrink-0 text-cyan-600">·</span>
            Exporte für WP, DMS &amp; DATEV-Pipelines
          </li>
        </ul>
        <div className="mt-auto pt-4">
          <div className="h-2 overflow-hidden rounded-full bg-slate-200">
            <div className="h-full w-[72%] rounded-full bg-gradient-to-r from-cyan-500 to-teal-500" />
          </div>
        </div>
      </div>
    ),
  },
  {
    id: "nis2",
    label: "NIS2 / KRITIS",
    icon: "🛡️",
    content: (
      <div className="flex h-full flex-col p-6">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Incident &amp; Supply Chain
        </div>
        <div className="mt-4 flex h-32 items-end gap-2 sm:gap-3">
          {[45, 72, 58, 88, 64].map((h, i) => (
            <div key={i} className="flex h-full min-w-0 flex-1 flex-col justify-end">
              <div
                className="w-full rounded-t-lg bg-gradient-to-t from-slate-800 to-slate-600 shadow-inner"
                style={{ height: `${h}%` }}
              />
            </div>
          ))}
        </div>
        <div className="mt-2 flex justify-between text-[0.65rem] text-slate-500">
          <span>Incident</span>
          <span>Supplier</span>
          <span>OT/IT</span>
        </div>
        <ul className="mt-4 space-y-2 text-left text-sm leading-snug text-slate-600">
          <li className="flex gap-2">
            <span className="shrink-0 text-cyan-600">·</span>
            Incident Readiness &amp; BC/DR-Bezug
          </li>
          <li className="flex gap-2">
            <span className="shrink-0 text-cyan-600">·</span>
            Supplier Risk &amp; Lieferketten-Sicht
          </li>
          <li className="flex gap-2">
            <span className="shrink-0 text-cyan-600">·</span>
            OT/IT-Segregation für KRITIS-relevante Kontexte
          </li>
        </ul>
      </div>
    ),
  },
  {
    id: "euai",
    label: "EU AI Act",
    icon: "🤖",
    content: (
      <div className="flex h-full flex-col p-6 text-center">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          High-Risk Readiness
        </div>
        <div className="relative mx-auto mt-3 h-28 w-28">
          <div
            className="absolute inset-0 rounded-full"
            style={{
              background: `conic-gradient(rgb(8 145 178) 0% 68%, rgb(226 232 240) 68% 100%)`,
            }}
          />
          <div className="absolute inset-[10px] flex items-center justify-center rounded-full bg-white shadow-inner">
            <span className="text-2xl font-semibold tabular-nums text-slate-900">68%</span>
          </div>
        </div>
        <ul className="mt-4 space-y-2 text-left text-sm leading-snug text-slate-600">
          <li className="flex gap-2">
            <span className="shrink-0 text-cyan-600">·</span>
            High-Risk-Systeme &amp; Pflichtcontrols im Fokus
          </li>
          <li className="flex gap-2">
            <span className="shrink-0 text-cyan-600">·</span>
            Readiness-Score bis Stichtag 02.08.2026
          </li>
          <li className="flex gap-2">
            <span className="shrink-0 text-cyan-600">·</span>
            Maßnahmen-Tracking mit Owner &amp; Fälligkeit
          </li>
        </ul>
        <p className="mt-3 text-xs text-slate-500">
          Ziel: 85&nbsp;% vor dem Stichtag ·{" "}
          <time dateTime="2026-08-02">02.08.2026</time>
        </p>
      </div>
    ),
  },
] as const;

export function HomeHeroSlides() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const t = window.setInterval(() => {
      setActive((i) => (i + 1) % slides.length);
    }, 7000);
    return () => window.clearInterval(t);
  }, []);

  return (
    <div className="min-w-0">
      <div
        className="relative min-h-[300px] overflow-hidden rounded-3xl border border-slate-200/80 bg-gradient-to-br from-white via-slate-50 to-cyan-50/40 shadow-lg shadow-slate-300/40 sm:min-h-[340px]"
        role="region"
        aria-roledescription="carousel"
        aria-label="Produktüberblick"
      >
        {slides.map((s, i) => (
          <div
            key={s.id}
            className={`absolute inset-0 transition-opacity duration-500 ease-out ${
              i === active ? "z-10 opacity-100" : "z-0 pointer-events-none opacity-0"
            }`}
            aria-hidden={i !== active}
          >
            {s.content}
          </div>
        ))}
      </div>
      <div
        className="mt-4 flex flex-wrap justify-center gap-2"
        role="tablist"
        aria-label="Bereiche"
      >
        {slides.map((s, i) => (
          <button
            key={s.id}
            type="button"
            role="tab"
            aria-selected={i === active}
            className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
              i === active
                ? "border-cyan-600/30 bg-cyan-600 text-white shadow-sm"
                : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50"
            }`}
            onClick={() => setActive(i)}
          >
            <span aria-hidden>{s.icon}</span>
            {s.label}
          </button>
        ))}
      </div>
      <div className="mt-3 flex justify-center gap-1.5" aria-hidden>
        {slides.map((_, i) => (
          <span
            key={i}
            className={`h-1.5 rounded-full transition-all ${
              i === active ? "w-6 bg-cyan-600" : "w-1.5 bg-slate-300"
            }`}
          />
        ))}
      </div>
    </div>
  );
}
