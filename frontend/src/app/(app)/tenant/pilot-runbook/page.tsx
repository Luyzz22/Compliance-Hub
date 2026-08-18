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
import { featurePilotRunbook } from "@/lib/config";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

export default async function PilotRunbookPage() {
  if (!featurePilotRunbook()) {
    notFound();
  }

  const tenantId = await getWorkspaceTenantIdServer();

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Pilot"
        title="Pilot-Runbook"
        description="Leitfaden für Projektleitung, CISO und Fachbereich – strukturierter Ablauf für AI-Act-Readiness, NIS2-KPIs und Board-taugliche Nachweise."
        actions={
          <Link href="/tenant/compliance-overview" className={`${CH_BTN_SECONDARY} text-sm`}>
            Zur Compliance-Übersicht
          </Link>
        }
      />

      <p className="mb-6 text-sm text-slate-500">
        Mandant: <span className="font-mono font-semibold text-slate-800">{tenantId}</span>
      </p>

      <div className="space-y-6">
        <section className={CH_CARD} aria-labelledby="runbook-ziel">
          <h2 id="runbook-ziel" className={CH_SECTION_LABEL}>
            Zielbild
          </h2>
          <ul className="mt-3 list-inside list-disc space-y-2 text-sm text-slate-700">
            <li>
              <strong>EU AI Act Readiness:</strong> Register, Klassifikation, Lücken und Maßnahmen
              nachvollziehbar dokumentiert.
            </li>
            <li>
              <strong>NIS2 / KRITIS:</strong> KPIs zu Incidents, Lieferanten und OT/IT als
              steuerbare Kennzahlen.
            </li>
            <li>
              <strong>Board und Aufsicht:</strong> KPI-Dashboards, Reports und Evidenzen für
              Vorstand und Prüfer vorbereiten.
            </li>
          </ul>
        </section>

        <section className={CH_CARD} aria-labelledby="runbook-wochen">
          <h2 id="runbook-wochen" className={CH_SECTION_LABEL}>
            Wochenplan (4–6 Wochen)
          </h2>
          <ol className="mt-3 list-inside list-decimal space-y-3 text-sm text-slate-700">
            <li>
              <strong>Woche 1:</strong> KI-Inventar erfassen, Risiko grob einordnen, Klassifikation
              starten.
            </li>
            <li>
              <strong>Woche 2–3:</strong> NIS2-/KRITIS-KPIs je System befüllen, Policies und
              Verantwortliche zuordnen.
            </li>
            <li>
              <strong>Woche 3–4:</strong> Governance-Actions umsetzen, Nachweise (Evidence) an
              kritische Systeme und Anforderungen hängen.
            </li>
            <li>
              <strong>Woche 5–6:</strong> Board-Demo vorbereiten, Exporte testen; bei Berater-Pilot
              Mandanten-Steckbrief / Report abstimmen.
            </li>
          </ol>
        </section>

        <section className={CH_CARD} aria-labelledby="runbook-rollen">
          <h2 id="runbook-rollen" className={CH_SECTION_LABEL}>
            Empfohlene Rollen
          </h2>
          <ul className="mt-3 list-inside list-disc space-y-2 text-sm text-slate-700">
            <li>
              <strong>CISO / Informationssicherheit:</strong> Policies, KPIs, Incident-Readiness.
            </li>
            <li>
              <strong>AI-System-Owner:</strong> fachliche Beschreibung, Daten, Lieferanten,
              Betriebsprozesse.
            </li>
            <li>
              <strong>Legal / Datenschutz:</strong> DPIA, Verarbeitungstätigkeiten, Transparenz
              beim EU AI Act.
            </li>
          </ul>
        </section>

        <section className={CH_CARD} aria-labelledby="runbook-check">
          <h2 id="runbook-check" className={CH_SECTION_LABEL}>
            Checkliste
          </h2>
          <ul className="mt-3 space-y-2 text-sm text-slate-700">
            <li className="flex flex-wrap items-center gap-2">
              <span className="rounded border border-slate-200 bg-white px-2 py-0.5 text-xs font-semibold text-slate-600">
                Setup
              </span>
              <Link
                href="/tenant/compliance-overview"
                className="font-medium text-cyan-800 underline decoration-cyan-300 underline-offset-2 hover:text-cyan-950"
              >
                Guided Setup in der Compliance-Übersicht abschließen
              </Link>
            </li>
            <li className="flex flex-wrap items-center gap-2">
              <span className="rounded border border-slate-200 bg-white px-2 py-0.5 text-xs font-semibold text-slate-600">
                Board
              </span>
              <Link href="/board/kpis" className={`${CH_BTN_PRIMARY} inline-flex text-xs no-underline`}>
                Board-KPIs öffnen
              </Link>
              <Link
                href="/board/nis2-kritis"
                className={`${CH_BTN_SECONDARY} inline-flex text-xs no-underline`}
              >
                NIS2 / KRITIS
              </Link>
            </li>
            <li className="flex flex-wrap items-center gap-2">
              <span className="rounded border border-slate-200 bg-white px-2 py-0.5 text-xs font-semibold text-slate-600">
                Berater
              </span>
              <span className="text-slate-600">
                Steckbrief / Report über den Advisor-Workspace (wenn zugeordnet).
              </span>
            </li>
          </ul>
        </section>
      </div>
    </div>
  );
}
