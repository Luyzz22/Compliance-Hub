import Link from "next/link";
import React from "react";

import { HomeHeroSlides } from "@/components/home/HomeHeroSlides";
import { CH_BTN_PRIMARY, CH_BTN_SECONDARY, CH_CARD } from "@/lib/boardLayout";

export default function HomePage() {
  return (
    <div className="min-w-0 space-y-16 md:space-y-20">
      <section className="grid gap-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:gap-12">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-700">
            Board-ready · DACH · Enterprise
          </p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl sm:leading-[1.08]">
            Board-ready AI Governance für EU AI Act &amp; NIS2
          </h1>
          <p className="mt-4 max-w-xl text-lg leading-relaxed text-slate-600">
            Auditierbare Reifegrade, regulatorische KPIs und offene Maßnahmen – für
            Vorstand, ISB und externe Prüfer. Stichtag High-Risk:{" "}
            <time dateTime="2026-08-02" className="font-medium text-slate-800">
              02.08.2026
            </time>
            .
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/board/kpis" className={CH_BTN_PRIMARY}>
              Board öffnen
            </Link>
            <Link href="/settings" className={CH_BTN_SECONDARY}>
              Mandant &amp; Einstellungen
            </Link>
          </div>
        </div>
        <HomeHeroSlides />
      </section>

      <section aria-label="Enterprise-Funktionen">
        <h2 className="sr-only">Enterprise-Funktionen</h2>
        <div className="grid gap-6 md:grid-cols-2">
          <article className={CH_CARD}>
            <div className="flex items-start gap-3">
              <span className="text-2xl" aria-hidden>
                📊
              </span>
              <div className="min-w-0 flex-1">
                <span className="inline-block rounded-full bg-cyan-50 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-cyan-800">
                  Board
                </span>
                <h4 className="mt-3 text-lg font-semibold text-slate-900">
                  Board-Readiness &amp; Executive KPIs
                </h4>
                <ul className="mt-3 space-y-1.5 text-sm text-slate-600">
                  <li>Einheitliche KPI-Leiste für Aufsicht &amp; NIS2-Reporting</li>
                  <li>Alerts mit Drilldown zu Incidents &amp; Systemen</li>
                  <li>Exportpfade für Prüfer &amp; Berater (JSON/CSV/Report)</li>
                </ul>
                <Link
                  href="/board/kpis"
                  className={`${CH_BTN_PRIMARY} mt-6 inline-flex w-full sm:w-auto`}
                >
                  Zum Board
                </Link>
              </div>
            </div>
          </article>

          <article className={CH_CARD}>
            <div className="flex items-start gap-3">
              <span className="text-2xl" aria-hidden>
                🛡️
              </span>
              <div className="min-w-0 flex-1">
                <span className="inline-block rounded-full bg-slate-100 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-slate-700">
                  NIS2
                </span>
                <h4 className="mt-3 text-lg font-semibold text-slate-900">
                  NIS2 / KRITIS &amp; persönliche Verantwortung
                </h4>
                <ul className="mt-3 space-y-1.5 text-sm text-slate-600">
                  <li>Incident-Readiness &amp; Lieferketten-Risiko transparent</li>
                  <li>OT/IT-Segregation &amp; „Worst Offenders“ pro KPI-Typ</li>
                  <li>Haftungsrelevante Lücken priorisiert sichtbar</li>
                </ul>
                <Link
                  href="/board/nis2-kritis"
                  className={`${CH_BTN_SECONDARY} mt-6 inline-flex w-full sm:w-auto`}
                >
                  NIS2-Drilldown
                </Link>
              </div>
            </div>
          </article>

          <article className={CH_CARD}>
            <div className="flex items-start gap-3">
              <span className="text-2xl" aria-hidden>
                🤖
              </span>
              <div className="min-w-0 flex-1">
                <span className="inline-block rounded-full bg-amber-50 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-amber-900">
                  EU AI Act
                </span>
                <h4 className="mt-3 text-lg font-semibold text-slate-900">
                  EU AI Act Readiness &amp; High-Risk
                </h4>
                <ul className="mt-3 space-y-1.5 text-sm text-slate-600">
                  <li>Readiness-Score, Tage bis Stichtag, kritische Artikel</li>
                  <li>Verknüpfung zu betroffenen Systemen &amp; Maßnahmen</li>
                  <li>Roadmap-QPs für Q2/Q3 2026 im Blick</li>
                </ul>
                <Link
                  href="/board/eu-ai-act-readiness"
                  className={`${CH_BTN_PRIMARY} mt-6 inline-flex w-full sm:w-auto`}
                >
                  Readiness-Dashboard
                </Link>
              </div>
            </div>
          </article>

          <article
            className={`${CH_CARD} border-dashed border-cyan-200/80 bg-gradient-to-br from-white to-cyan-50/30`}
          >
            <div className="flex items-start gap-3">
              <span className="text-2xl" aria-hidden>
                ✅
              </span>
              <div className="min-w-0 flex-1">
                <span className="inline-block rounded-full bg-white/80 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-slate-700">
                  Audit
                </span>
                <h4 className="mt-3 text-lg font-semibold text-slate-900">
                  Auditor-ready &amp; DATEV-orientiert
                </h4>
                <ul className="mt-3 space-y-1.5 text-sm text-slate-600">
                  <li>Strukturierte Reports für DMS, WP &amp; Kanzlei</li>
                  <li>Nachvollziehbare KPI- und Alert-Exporte</li>
                  <li>Mandanten-Cockpit für Policies &amp; Register</li>
                </ul>
                <div className="mt-6 flex flex-wrap gap-2">
                  <Link href="/board/kpis" className={CH_BTN_SECONDARY}>
                    Exporte &amp; Reports
                  </Link>
                  <Link href="/incidents" className={CH_BTN_PRIMARY}>
                    Incidents
                  </Link>
                </div>
              </div>
            </div>
          </article>
        </div>
      </section>
    </div>
  );
}
