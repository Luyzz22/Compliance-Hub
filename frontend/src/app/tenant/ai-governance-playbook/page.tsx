import Link from "next/link";
import { notFound } from "next/navigation";
import React from "react";

import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_SECTION_LABEL,
  CH_SHELL,
} from "@/lib/boardLayout";
import {
  featureAiComplianceBoardReport,
  featureAiGovernancePlaybook,
  featureCrossRegulationDashboard,
} from "@/lib/config";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

import {
  PILOT_WEEKS,
  PLAYBOOK_PHASES,
  RACI_ROLES,
  RACI_ROWS,
  type RaciCell,
} from "./model";

function raciCellClass(v: RaciCell): string {
  if (v === "A") return "bg-slate-900 font-bold text-white";
  if (v === "R") return "bg-cyan-700 font-semibold text-white";
  if (v === "C") return "bg-amber-100 font-semibold text-amber-950";
  if (v === "I") return "bg-slate-100 font-medium text-slate-700";
  return "bg-white text-slate-400";
}

export default async function AiGovernancePlaybookPage() {
  if (!featureAiGovernancePlaybook()) {
    notFound();
  }

  const tenantId = await getWorkspaceTenantIdServer();

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Tenant"
        title="AI Governance Playbook"
        description="Rollen, RACI, Phasenplan und Pilot-Ablauf – operative Projektsteuerung für CISO, AI-Governance-Lead und Projektleitung im Mandanten-Workspace."
        actions={
          <Link href="/tenant/compliance-overview" className={`${CH_BTN_SECONDARY} text-sm`}>
            Zur Compliance-Übersicht
          </Link>
        }
      />

      <p className="mb-6 text-sm text-slate-500">
        Mandant: <span className="font-mono font-semibold text-slate-800">{tenantId}</span>
      </p>

      {featureAiComplianceBoardReport() ? (
        <section
          className={`${CH_CARD} mb-8 border-cyan-200 bg-cyan-50/40`}
          aria-label="Board-Report"
          data-testid="playbook-board-report-hint"
        >
          <p className={CH_SECTION_LABEL}>Board-Report</p>
          <p className="mt-2 max-w-3xl text-sm text-slate-700">
            Aus Coverage, Gaps und KI-Empfehlungen ein konsistentes Markdown-Snippet für Vorstand,
            Management oder Mandantenreports erzeugen.
          </p>
          <Link
            href="/board/ai-compliance-report"
            className={`${CH_BTN_PRIMARY} mt-4 inline-flex text-sm no-underline`}
          >
            AI Compliance Report öffnen
          </Link>
        </section>
      ) : null}

      <section className={CH_CARD} aria-labelledby="playbook-raci-heading" data-testid="playbook-raci">
        <h2 id="playbook-raci-heading" className={CH_SECTION_LABEL}>
          Governance-Rollen &amp; RACI
        </h2>
        <p className="mt-2 max-w-4xl text-sm text-slate-600">
          Verantwortlichkeiten für Kernaufgaben – orientiert an ISO 42001 und gängiger AI-Governance-
          Praxis. Die Rollen sind eine <strong>inhaltliche Orientierung</strong> im UI, kein technisches
          RBAC.
        </p>

        <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200">
          <table className="min-w-[720px] w-full border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th scope="col" className="sticky left-0 z-10 bg-slate-50 px-3 py-2 font-semibold text-slate-800">
                  Aufgabe
                </th>
                {RACI_ROLES.map((r) => (
                  <th
                    key={r.id}
                    scope="col"
                    className="min-w-[4.5rem] px-1 py-2 text-center font-semibold text-slate-700"
                    title={r.label}
                  >
                    <span className="block leading-tight">{r.short}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {RACI_ROWS.map((row) => (
                <tr key={row.id} className="border-b border-slate-100 last:border-0">
                  <th
                    scope="row"
                    className="sticky left-0 z-10 bg-white px-3 py-2 align-top font-normal text-slate-800"
                  >
                    <span className="font-semibold">{row.task}</span>
                    <span className="mt-0.5 block text-[11px] text-slate-500">{row.ref}</span>
                  </th>
                  {RACI_ROLES.map((role) => {
                    const v = row.cells[role.id] ?? "—";
                    return (
                      <td key={role.id} className="px-1 py-1.5 text-center align-middle">
                        <span
                          className={`inline-flex h-8 w-8 items-center justify-center rounded-md text-[11px] ${raciCellClass(v)}`}
                          title={`${role.label}: ${v}`}
                        >
                          {v}
                        </span>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <dl className="mt-4 grid gap-2 text-xs text-slate-600 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <dt className="font-semibold text-slate-800">R – Responsible</dt>
            <dd>Umsetzung / operative Erledigung</dd>
          </div>
          <div>
            <dt className="font-semibold text-slate-800">A – Accountable</dt>
            <dd>Endverantwortung, Freigabe</dd>
          </div>
          <div>
            <dt className="font-semibold text-slate-800">C – Consulted</dt>
            <dd>Einbindung vor Entscheidung</dd>
          </div>
          <div>
            <dt className="font-semibold text-slate-800">I – Informed</dt>
            <dd>Information über Ergebnisse / Status</dd>
          </div>
        </dl>

        <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 text-xs text-slate-600">
          <strong className="text-slate-800">Rollenlegende:</strong>{" "}
          {RACI_ROLES.map((r) => (
            <span key={r.id} className="mr-3 inline-block">
              <span className="font-semibold text-slate-700">{r.short}:</span> {r.label}
            </span>
          ))}
        </div>
      </section>

      <section
        className="mt-8"
        aria-labelledby="playbook-phases-heading"
        data-testid="playbook-phases"
      >
        <h2 id="playbook-phases-heading" className={`${CH_SECTION_LABEL} mb-4`}>
          Phasenplan: Readiness → Operational → Excellence
        </h2>
        <p className="mb-6 max-w-4xl text-sm text-slate-600">
          Drei Stufen aus der Produkt-Roadmap – von der Pflichtbasis bis zu Cross-Regulation und
          Prüfungsreife. Aufgaben verlinken direkt in die Module von Compliance Hub.
        </p>
        <div className="grid gap-5 lg:grid-cols-3">
          {PLAYBOOK_PHASES.map((phase) => (
            <article key={phase.id} className={`${CH_CARD} flex flex-col`}>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[11px] font-bold uppercase tracking-wide text-cyan-800">
                  {phase.stage}
                </span>
                {phase.badges.map((b) => (
                  <span
                    key={b}
                    className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-semibold text-slate-600"
                  >
                    {b}
                  </span>
                ))}
              </div>
              <h3 className="mt-2 text-base font-bold text-slate-900">{phase.title}</h3>
              <p className="text-xs font-medium text-slate-500">{phase.horizon}</p>
              <p className="mt-2 flex-1 text-sm text-slate-600">{phase.description}</p>
              <div className="mt-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Kernziele
                </p>
                <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-slate-700">
                  {phase.goals.map((g) => (
                    <li key={g}>{g}</li>
                  ))}
                </ul>
              </div>
              <div className="mt-4 border-t border-slate-200 pt-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Aufgaben
                </p>
                <ul className="mt-3 space-y-2">
                  {phase.tasks.map((t) => (
                    <li key={t.label}>
                      <Link
                        href={t.href}
                        className={`${CH_BTN_PRIMARY} inline-flex w-full justify-center text-xs sm:w-auto`}
                        data-testid="playbook-phase-link"
                      >
                        {t.label}
                      </Link>
                      {t.hint ? (
                        <p className="mt-1 text-[11px] leading-snug text-slate-500">{t.hint}</p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            </article>
          ))}
        </div>
      </section>

      {featureCrossRegulationDashboard() ? (
        <section
          className={`${CH_CARD} mt-8 border-slate-300 bg-slate-50/80`}
          aria-labelledby="playbook-cross-reg-heading"
        >
          <h2 id="playbook-cross-reg-heading" className={CH_SECTION_LABEL}>
            Schritt 2: Frameworks konsolidieren
          </h2>
          <p className="mt-2 max-w-3xl text-sm text-slate-700">
            Öffnen Sie das Cross-Regulation Dashboard, um zu sehen, welche regulatorischen Pflichten durch
            Ihre Controls abgedeckt sind – und wo noch Lücken bestehen (Map once, comply many).
          </p>
          <Link
            href="/tenant/cross-regulation-dashboard"
            className={`${CH_BTN_PRIMARY} mt-4 inline-flex text-xs`}
          >
            Cross-Regulation Dashboard
          </Link>
        </section>
      ) : null}

      <section className={`${CH_CARD} mt-8`} aria-labelledby="playbook-pilot-heading">
        <h2 id="playbook-pilot-heading" className={CH_SECTION_LABEL}>
          So nutzen Sie Compliance Hub im Pilot (4–6 Wochen)
        </h2>
        <p className="mt-2 max-w-4xl text-sm text-slate-600">
          Kompakter Ablauf für einen fokussierten Piloten – abgestimmt mit dem Pilot-Runbook und dem
          E2E-Demo-Flow. Jede Woche mit direkten Einstiegen in Workspace und Board.
        </p>
        <ol className="mt-6 space-y-5">
          {PILOT_WEEKS.map((w) => (
            <li
              key={w.week}
              className="rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-3"
            >
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="text-sm font-bold text-cyan-900">{w.week}</span>
                <span className="text-sm font-semibold text-slate-900">{w.title}</span>
              </div>
              <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-slate-700">
                {w.bullets.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
              <div className="mt-3 flex flex-wrap gap-2">
                {w.links.map((l) => (
                  <Link
                    key={l.href + l.label}
                    href={l.href}
                    className={`${CH_BTN_SECONDARY} text-xs`}
                    data-testid="playbook-pilot-link"
                  >
                    {l.label}
                  </Link>
                ))}
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section
        className={`${CH_CARD} mt-8 border-cyan-200 bg-cyan-50/40`}
        aria-labelledby="playbook-advisor-heading"
      >
        <h2 id="playbook-advisor-heading" className={CH_SECTION_LABEL}>
          Für Berater
        </h2>
        <p className="mt-2 text-sm text-slate-700">
          Nutzen Sie den <Link className="font-semibold text-cyan-900 underline" href="/advisor">
            Advisor-Workspace
          </Link>
          , Mandanten-Steckbriefe und das Guided Setup <strong>je Mandant</strong>. Demo-Tenants und
          Template-Seeding beschleunigen Workshops – nur mit freigegebener Demo-Allowlist.
        </p>
        <p className="mt-2 text-sm text-slate-700">
          <strong>RACI-Sicht:</strong> Berater sind typischerweise <strong>R</strong> oder{" "}
          <strong>A/R</strong> bei Setup, Inventar und Gap-Analyse; der Kunde bleibt{" "}
          <strong>A</strong> bei Governance-Entscheidungen, Freigaben und Policy-Verantwortung.
        </p>
      </section>
    </div>
  );
}
