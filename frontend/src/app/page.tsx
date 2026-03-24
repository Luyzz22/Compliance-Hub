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
            Eine ruhige, auditierbare Sicht auf Reifegrad, regulatorische KPIs und
            offene Maßnahmen – gebaut für Vorstand, ISB und externe Prüfer.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/board/kpis" className={CH_BTN_PRIMARY}>
              Board öffnen
            </Link>
            <Link href="/tenant/compliance-overview" className={CH_BTN_SECONDARY}>
              Tenant-Cockpit
            </Link>
          </div>
        </div>
        <HomeHeroSlides />
      </section>

      <section aria-label="Kernmodule">
        <h2 className="sr-only">Kernmodule</h2>
        <div className="grid gap-6 md:grid-cols-2">
          <article className={CH_CARD}>
            <div className="flex items-start justify-between gap-3">
              <span className="text-2xl" aria-hidden>
                📊
              </span>
              <span className="rounded-full bg-cyan-50 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-cyan-800">
                Board
              </span>
            </div>
            <h3 className="mt-4 text-xl font-semibold text-slate-900">Board KPIs</h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">
              ISO-42001-Reife, NIS2-Incident- und Supplier-Kennzahlen, Alerts und
              Exporte für CISO und Aufsicht.
            </p>
            <dl className="mt-5 grid grid-cols-3 gap-3 border-t border-slate-100 pt-5 text-center">
              <div>
                <dt className="text-[0.65rem] font-medium uppercase tracking-wide text-slate-500">
                  Reife
                </dt>
                <dd className="mt-1 text-lg font-semibold tabular-nums text-slate-900">
                  Live
                </dd>
              </div>
              <div>
                <dt className="text-[0.65rem] font-medium uppercase tracking-wide text-slate-500">
                  Alerts
                </dt>
                <dd className="mt-1 text-lg font-semibold tabular-nums text-slate-900">
                  API
                </dd>
              </div>
              <div>
                <dt className="text-[0.65rem] font-medium uppercase tracking-wide text-slate-500">
                  Export
                </dt>
                <dd className="mt-1 text-lg font-semibold tabular-nums text-slate-900">
                  JSON
                </dd>
              </div>
            </dl>
            <Link
              href="/board/kpis"
              className={`${CH_BTN_PRIMARY} mt-6 w-full sm:w-auto`}
            >
              Board öffnen
            </Link>
          </article>

          <article className={CH_CARD}>
            <div className="flex items-start justify-between gap-3">
              <span className="text-2xl" aria-hidden>
                🛡️
              </span>
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-slate-700">
                NIS2
              </span>
            </div>
            <h3 className="mt-4 text-xl font-semibold text-slate-900">NIS2 / KRITIS</h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">
              Verteilung und schwächste Systeme je KPI-Typ – für
              Aufsichtsreporting und KRITIS-Bezug.
            </p>
            <ul className="mt-4 space-y-2 text-sm text-slate-600">
              <li className="flex gap-2">
                <span className="text-cyan-600">·</span>
                Incident-Response- und Backup-Runbook-Reife
              </li>
              <li className="flex gap-2">
                <span className="text-cyan-600">·</span>
                Supplier-Risk-Coverage und Supply-Chain-Sicht
              </li>
            </ul>
            <Link
              href="/board/nis2-kritis"
              className={`${CH_BTN_SECONDARY} mt-6 w-full sm:w-auto`}
            >
              NIS2-Drilldown
            </Link>
          </article>

          <article className={CH_CARD}>
            <div className="flex items-start justify-between gap-3">
              <span className="text-2xl" aria-hidden>
                🤖
              </span>
              <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-amber-900">
                EU AI Act
              </span>
            </div>
            <h3 className="mt-4 text-xl font-semibold text-slate-900">EU AI Act Readiness</h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">
              High-Risk-Fokus, kritische Anforderungen und Verknüpfung zu
              Maßnahmen und Systemen.
            </p>
            <p className="mt-4 rounded-xl bg-slate-50 px-3 py-2 text-sm font-medium text-slate-800">
              Stichtag High-Risk:{" "}
              <time dateTime="2026-08-02">02.08.2026</time>
            </p>
            <Link
              href="/board/eu-ai-act-readiness"
              className={`${CH_BTN_PRIMARY} mt-6 w-full sm:w-auto`}
            >
              Readiness-Dashboard
            </Link>
          </article>

          <article className={`${CH_CARD} border-dashed border-cyan-200/80 bg-gradient-to-br from-white to-cyan-50/30`}>
            <div className="flex items-start justify-between gap-3">
              <span className="text-2xl" aria-hidden>
                📁
              </span>
              <span className="rounded-full bg-white/80 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-slate-700">
                Audit
              </span>
            </div>
            <h3 className="mt-4 text-xl font-semibold text-slate-900">
              Audit-Ready / Beratermodus
            </h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">
              Board-Reports, KPI-Exporte und Prüfspuren – strukturiert für DMS,
              Kanzlei und DATEV-Pipelines.
            </p>
            <Link href="/board/kpis" className={`${CH_BTN_SECONDARY} mt-6 w-full sm:w-auto`}>
              Zu Exporten &amp; Reports
            </Link>
          </article>
        </div>
      </section>
    </div>
  );
}
