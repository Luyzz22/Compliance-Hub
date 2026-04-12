import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_SECTION_LABEL,
  CH_SHELL,
} from "@/lib/boardLayout";
import Link from "next/link";

const frameworks = [
  { key: "EU_AI_ACT", label: "EU AI Act", color: "bg-purple-100 text-purple-800" },
  { key: "ISO_42001", label: "ISO 42001", color: "bg-indigo-100 text-indigo-800" },
  { key: "ISO_27001", label: "ISO 27001", color: "bg-cyan-100 text-cyan-800" },
  { key: "NIS2", label: "NIS2", color: "bg-amber-100 text-amber-800" },
  { key: "DSGVO", label: "DSGVO", color: "bg-blue-100 text-blue-800" },
  { key: "GoBD", label: "GoBD", color: "bg-emerald-100 text-emerald-800" },
];

/**
 * Sample control data for the compliance mapping matrix.
 * In production this would be fetched from the API.
 */
const sampleControls = [
  {
    id: "ctrl-1",
    title: "Zugriffssteuerung & RBAC",
    type: "tom",
    coverage: { EU_AI_ACT: "partial", ISO_42001: "full", ISO_27001: "full", NIS2: "full", DSGVO: "full", GoBD: "partial" },
  },
  {
    id: "ctrl-2",
    title: "Audit-Trail & Nachvollziehbarkeit",
    type: "tom",
    coverage: { EU_AI_ACT: "full", ISO_42001: "full", ISO_27001: "full", NIS2: "full", DSGVO: "full", GoBD: "full" },
  },
  {
    id: "ctrl-3",
    title: "Incident-Management & Response",
    type: "tom",
    coverage: { EU_AI_ACT: "partial", ISO_42001: "partial", ISO_27001: "full", NIS2: "full", DSGVO: "partial", GoBD: "not_applicable" },
  },
  {
    id: "ctrl-4",
    title: "KI-Register & Risikoklassifikation",
    type: "tom",
    coverage: { EU_AI_ACT: "full", ISO_42001: "full", ISO_27001: "not_applicable", NIS2: "partial", DSGVO: "partial", GoBD: "not_applicable" },
  },
  {
    id: "ctrl-5",
    title: "Datenschutz-Folgenabschätzung",
    type: "tom",
    coverage: { EU_AI_ACT: "full", ISO_42001: "partial", ISO_27001: "partial", NIS2: "partial", DSGVO: "full", GoBD: "not_applicable" },
  },
  {
    id: "ctrl-6",
    title: "Verschlüsselung & Datensicherheit",
    type: "tom",
    coverage: { EU_AI_ACT: "partial", ISO_42001: "partial", ISO_27001: "full", NIS2: "full", DSGVO: "full", GoBD: "partial" },
  },
  {
    id: "ctrl-7",
    title: "Lieferketten- & Drittanbieter-Management",
    type: "tom",
    coverage: { EU_AI_ACT: "partial", ISO_42001: "partial", ISO_27001: "full", NIS2: "full", DSGVO: "partial", GoBD: "not_applicable" },
  },
  {
    id: "ctrl-8",
    title: "GoBD-konforme Belegarchivierung",
    type: "tom",
    coverage: { EU_AI_ACT: "not_applicable", ISO_42001: "not_applicable", ISO_27001: "partial", NIS2: "not_applicable", DSGVO: "partial", GoBD: "full" },
  },
];

function coverageCell(level: string) {
  switch (level) {
    case "full":
      return (
        <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100 text-emerald-700" title="Vollständig">
          <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </span>
      );
    case "partial":
      return (
        <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-amber-100 text-amber-700" title="Teilweise">
          <span className="text-xs font-bold">~</span>
        </span>
      );
    case "planned":
      return (
        <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-blue-100 text-blue-700" title="Geplant">
          <span className="text-xs font-bold">○</span>
        </span>
      );
    default:
      return (
        <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-slate-100 text-slate-400" title="Nicht zutreffend">
          <span className="text-xs">–</span>
        </span>
      );
  }
}

export default function TenantComplianceMappingPage() {
  // Compute coverage stats
  const coverageStats = frameworks.map((fw) => {
    const total = sampleControls.length;
    const covered = sampleControls.filter(
      (c) => c.coverage[fw.key as keyof typeof c.coverage] === "full" || c.coverage[fw.key as keyof typeof c.coverage] === "partial"
    ).length;
    return { ...fw, covered, total, ratio: Math.round((covered / total) * 100) };
  });

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Trust Center"
        title="Compliance Mapping"
        description={
          <>
            „Map once, comply many" – Übersicht welche Controls und Nachweise auf welche
            Frameworks einzahlen. High-Level-Ansicht für Business/Procurement, Detail für
            Auditoren und Security Reviewer.
          </>
        }
        breadcrumbs={[
          { label: "Workspace", href: "/tenant/compliance-overview" },
          { label: "Trust Center", href: "/tenant/trust-center" },
          { label: "Compliance Mapping" },
        ]}
        actions={
          <Link
            href="/tenant/trust-center"
            className={`${CH_BTN_SECONDARY} text-sm`}
          >
            Zurück zum Assurance Portal
          </Link>
        }
      />

      {/* Framework Coverage Summary */}
      <section aria-label="Framework Coverage">
        <p className={CH_SECTION_LABEL}>Framework-Abdeckung</p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {coverageStats.map((fw) => (
            <div key={fw.key} className={CH_CARD}>
              <div className="flex items-center justify-between">
                <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[0.65rem] font-semibold ${fw.color}`}>
                  {fw.label}
                </span>
                <span className="text-sm font-semibold text-slate-900">{fw.ratio}%</span>
              </div>
              <div className="mt-2 h-2 rounded-full bg-slate-100">
                <div
                  className="h-2 rounded-full bg-cyan-500 transition-all"
                  style={{ width: `${fw.ratio}%` }}
                />
              </div>
              <p className="mt-1 text-xs text-slate-500">
                {fw.covered} von {fw.total} Controls abgedeckt
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Mapping Matrix */}
      <section aria-label="Compliance-Mapping-Matrix">
        <p className={CH_SECTION_LABEL}>Controls × Frameworks Matrix</p>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[700px] border-collapse">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="py-3 pr-4 text-left text-xs font-semibold text-slate-700">
                  Control / Nachweis
                </th>
                {frameworks.map((fw) => (
                  <th
                    key={fw.key}
                    className="px-2 py-3 text-center text-xs font-semibold text-slate-700"
                  >
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[0.6rem] font-semibold ${fw.color}`}>
                      {fw.label}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sampleControls.map((ctrl) => (
                <tr
                  key={ctrl.id}
                  className="border-b border-slate-100 hover:bg-slate-50/50 transition"
                >
                  <td className="py-3 pr-4 text-sm text-slate-800">{ctrl.title}</td>
                  {frameworks.map((fw) => (
                    <td key={fw.key} className="px-2 py-3 text-center">
                      {coverageCell(ctrl.coverage[fw.key as keyof typeof ctrl.coverage])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Legend */}
      <section aria-label="Legende" className={CH_CARD}>
        <p className={CH_SECTION_LABEL}>Legende</p>
        <div className="mt-3 flex flex-wrap gap-4">
          <div className="flex items-center gap-2">
            {coverageCell("full")}
            <span className="text-sm text-slate-600">Vollständig abgedeckt</span>
          </div>
          <div className="flex items-center gap-2">
            {coverageCell("partial")}
            <span className="text-sm text-slate-600">Teilweise abgedeckt</span>
          </div>
          <div className="flex items-center gap-2">
            {coverageCell("planned")}
            <span className="text-sm text-slate-600">Geplant</span>
          </div>
          <div className="flex items-center gap-2">
            {coverageCell("not_applicable")}
            <span className="text-sm text-slate-600">Nicht zutreffend</span>
          </div>
        </div>
      </section>
    </div>
  );
}
