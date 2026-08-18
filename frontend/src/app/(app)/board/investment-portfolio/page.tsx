import Link from "next/link";

import { CfoInvestmentScenarioExplorer } from "@/components/board/CfoInvestmentScenarioExplorer";
import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  fetchEnterpriseInvestmentPortfolio,
  type InvestmentDecisionDto,
  type InvestmentEnvelopeBandDto,
  type TimeToValueBandDto,
} from "@/lib/api";
import {
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_CARD_MUTED,
  CH_PAGE_NAV_LINK,
  CH_SECTION_LABEL,
  CH_SHELL,
} from "@/lib/boardLayout";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

const DECISION_LABELS: Record<InvestmentDecisionDto, string> = {
  fund_now: "Jetzt finanzieren",
  sequence: "Sequenzieren",
  validate: "Validieren",
  hold: "Halten",
};

const ENVELOPE_LABELS: Record<InvestmentEnvelopeBandDto, string> = {
  small: "Klein",
  medium: "Mittel",
  large: "Groß",
};

const TIME_TO_VALUE_LABELS: Record<TimeToValueBandDto, string> = {
  near_term: "Kurzfristig",
  mid_term: "Mittelfristig",
  long_term: "Langfristig",
};

export const metadata = {
  title: "CFO Investment Portfolio | ComplianceHub",
};

export default async function InvestmentPortfolioPage() {
  const tenantId = await getWorkspaceTenantIdServer();
  const portfolio = await fetchEnterpriseInvestmentPortfolio(tenantId, false);

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Board · Finance Governance"
        title="CFO Investment Portfolio"
        description="Nachvollziehbare Kapitalallokation für Compliance- und Integrationsvorhaben – mit sichtbaren Annahmen, Finance-Gates und reproduzierbaren Szenarien."
        breadcrumbs={[
          { label: "Board", href: "/board/executive-dashboard" },
          { label: "Investment Portfolio" },
        ]}
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href="/tenant/control-center" className={CH_BTN_SECONDARY}>
              Control Center
            </Link>
            <Link href="/tenant/onboarding-readiness" className={CH_BTN_SECONDARY}>
              Readiness prüfen
            </Link>
          </div>
        }
        below={
          <>
            <Link href="/board/executive-dashboard" className={CH_PAGE_NAV_LINK}>
              Executive Dashboard
            </Link>
            <Link href="/board/analytics" className={CH_PAGE_NAV_LINK}>
              Compliance Analytics
            </Link>
            <span className="text-sm text-slate-500">
              Stand {new Date(portfolio.generated_at_utc).toLocaleString("de-DE")}
            </span>
          </>
        }
      />

      <section aria-label="Portfolio-Zusammenfassung" className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SummaryCard
          label="Bewertete Initiativen"
          value={portfolio.summary.total_initiatives}
          detail="Tenant-isolierte Governance-Signale"
        />
        <SummaryCard
          label="Jetzt finanzieren"
          value={portfolio.summary.fund_now_count}
          detail="Nur nach Erfüllung aller Finance-Gates"
          accent="text-emerald-700"
        />
        <SummaryCard
          label="Sequenzieren"
          value={portfolio.summary.sequence_count}
          detail="Abhängigkeiten und Delivery-Reihenfolge klären"
          accent="text-cyan-800"
        />
        <SummaryCard
          label="Finance Inputs offen"
          value={portfolio.summary.missing_finance_inputs}
          detail="Euro-Korridor, Owner und Capex/Opex fehlen bewusst"
          accent="text-amber-800"
        />
      </section>

      <CfoInvestmentScenarioExplorer initiatives={portfolio.initiatives} />

      <section aria-labelledby="investment-boundaries-title" className="grid gap-5 lg:grid-cols-2">
        <article className={CH_CARD_MUTED}>
          <p className={CH_SECTION_LABEL}>Decision Integrity</p>
          <h2 id="investment-boundaries-title" className="mt-2 text-xl font-semibold text-slate-950">
            Kontrollierte Annahmen
          </h2>
          <ul className="mt-4 space-y-3 text-sm leading-6 text-slate-700">
            {portfolio.assumptions_de.map((assumption) => (
              <li key={assumption} className="flex gap-3">
                <span
                  aria-hidden
                  className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--sbs-navy-mid)]"
                />
                <span>{assumption}</span>
              </li>
            ))}
          </ul>
        </article>

        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Baseline-Logik</p>
          <h2 className="mt-2 text-xl font-semibold text-slate-950">
            100 % sichtbare Gewichtung
          </h2>
          <dl className="mt-5 grid grid-cols-2 gap-4 text-sm">
            <Weight label="Strategischer Wert" value={portfolio.baseline_weights.strategic_value_weight} />
            <Weight label="Risikoreduktion" value={portfolio.baseline_weights.risk_reduction_weight} />
            <Weight
              label="Ausführungssicherheit"
              value={portfolio.baseline_weights.execution_confidence_weight}
            />
            <Weight
              label="Kapitaleffizienz"
              value={portfolio.baseline_weights.capital_efficiency_weight}
            />
          </dl>
          <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
            Diese Ansicht ist eine relative Entscheidungshilfe. Sie ist weder Finanzprognose noch
            Budgetfreigabe und ersetzt keinen genehmigten Business Case.
          </div>
        </article>
      </section>

      <section aria-labelledby="baseline-register-title" className={CH_CARD}>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className={CH_SECTION_LABEL}>Board Decision Register</p>
            <h2 id="baseline-register-title" className="mt-2 text-xl font-semibold text-slate-950">
              Baseline und verbindliche Funding-Gates
            </h2>
          </div>
          <p className="max-w-xl text-sm text-slate-600">
            Die Rangfolge bleibt serverseitig deterministisch; Szenarien oben sind nicht persistent.
          </p>
        </div>

        <div className="mt-6 overflow-x-auto">
          <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-[0.1em] text-slate-500">
                <th scope="col" className="border-b border-slate-200 px-3 py-3 font-semibold">Rang</th>
                <th scope="col" className="border-b border-slate-200 px-3 py-3 font-semibold">Initiative</th>
                <th scope="col" className="border-b border-slate-200 px-3 py-3 font-semibold">Entscheidung</th>
                <th scope="col" className="border-b border-slate-200 px-3 py-3 font-semibold">Envelope</th>
                <th scope="col" className="border-b border-slate-200 px-3 py-3 font-semibold">Time-to-value</th>
                <th scope="col" className="border-b border-slate-200 px-3 py-3 font-semibold">Score</th>
              </tr>
            </thead>
            <tbody>
              {portfolio.initiatives.map((initiative) => (
                <tr key={initiative.initiative_id} className="align-top text-slate-700">
                  <td className="border-b border-slate-100 px-3 py-4 font-semibold text-slate-950">
                    {String(initiative.baseline_rank).padStart(2, "0")}
                  </td>
                  <td className="min-w-72 border-b border-slate-100 px-3 py-4">
                    <p className="font-semibold text-slate-950">{initiative.initiative_name_de}</p>
                    <p className="mt-1 text-xs leading-5 text-slate-500">
                      {initiative.decision_rationale_de}
                    </p>
                    <details className="mt-3">
                      <summary className="cursor-pointer text-xs font-semibold text-[var(--sbs-text-accent)]">
                        Funding-Gates und Quellen
                      </summary>
                      <ul className="mt-2 space-y-1 text-xs leading-5 text-slate-600">
                        {initiative.funding_preconditions_de.map((precondition) => (
                          <li key={precondition}>• {precondition}</li>
                        ))}
                      </ul>
                      <p className="mt-2 text-xs text-slate-500">
                        Quellen: {initiative.source_refs.join(" · ")}
                      </p>
                    </details>
                  </td>
                  <td className="whitespace-nowrap border-b border-slate-100 px-3 py-4 font-medium text-slate-950">
                    {DECISION_LABELS[initiative.recommended_decision]}
                  </td>
                  <td className="whitespace-nowrap border-b border-slate-100 px-3 py-4">
                    {ENVELOPE_LABELS[initiative.investment_envelope_band]}
                  </td>
                  <td className="whitespace-nowrap border-b border-slate-100 px-3 py-4">
                    {TIME_TO_VALUE_LABELS[initiative.time_to_value_band]}
                  </td>
                  <td className="border-b border-slate-100 px-3 py-4 font-semibold text-slate-950">
                    {initiative.portfolio_score}/100
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  detail,
  accent = "text-slate-950",
}: {
  label: string;
  value: number;
  detail: string;
  accent?: string;
}) {
  return (
    <article className={CH_CARD}>
      <p className={CH_SECTION_LABEL}>{label}</p>
      <p className={`mt-3 text-4xl font-semibold tracking-tight ${accent}`}>{value}</p>
      <p className="mt-2 text-xs leading-5 text-slate-500">{detail}</p>
    </article>
  );
}

function Weight({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
      <dt className="text-xs font-medium text-slate-600">{label}</dt>
      <dd className="mt-2 text-2xl font-semibold text-slate-950">{value}%</dd>
    </div>
  );
}
