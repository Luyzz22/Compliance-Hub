import Link from "next/link";

import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import { PreparationPackPreview } from "@/components/tenant/PreparationPackPreview";
import {
  fetchAuthorityAuditPreparationPack,
  fetchEnterpriseControlCenter,
  type ControlCenterSeverityDto,
  type PreparationPackFocusDto,
} from "@/lib/api";
import {
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_SECTION_LABEL,
  CH_SHELL,
} from "@/lib/boardLayout";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

function severityClass(sev: ControlCenterSeverityDto): string {
  if (sev === "critical") return "border-rose-300 bg-rose-50 text-rose-800";
  if (sev === "warning") return "border-amber-300 bg-amber-50 text-amber-900";
  return "border-slate-300 bg-slate-50 text-slate-700";
}

type PageProps = {
  searchParams?: Promise<{ generate_pack?: string; focus?: string }>;
};

export default async function TenantControlCenterPage({ searchParams }: PageProps) {
  const tenantId = await getWorkspaceTenantIdServer();
  const qp = (await searchParams) ?? {};
  const shouldGeneratePack = qp.generate_pack === "1";
  const focus =
    qp.focus === "audit" || qp.focus === "authority" || qp.focus === "mixed"
      ? (qp.focus as PreparationPackFocusDto)
      : "mixed";
  const data = await fetchEnterpriseControlCenter(tenantId, true);
  const prepPack = shouldGeneratePack
    ? await fetchAuthorityAuditPreparationPack(tenantId, focus)
    : null;

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Enterprise"
        title="Enterprise Control Center"
        description="Kompakter operativer Steuerungsblick auf kritische Governance-Signale, Fristen und Readiness-Blocker."
        actions={
          <div className="flex gap-2">
            <Link href="/tenant/compliance-overview" className={`${CH_BTN_SECONDARY} text-sm`}>
              Zur Compliance-Übersicht
            </Link>
            <Link
              href={`/tenant/control-center?generate_pack=1&focus=${focus}`}
              className={`${CH_BTN_SECONDARY} text-sm`}
            >
              Preparation Pack erstellen
            </Link>
          </div>
        }
      />

      <section className="grid gap-4 md:grid-cols-4">
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Kritisch</p>
          <p className="mt-2 text-3xl font-semibold text-rose-700">{data.summary_counts.critical}</p>
        </article>
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Warnung</p>
          <p className="mt-2 text-3xl font-semibold text-amber-700">{data.summary_counts.warning}</p>
        </article>
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Info</p>
          <p className="mt-2 text-3xl font-semibold text-slate-800">{data.summary_counts.info}</p>
        </article>
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Offene Punkte</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900">{data.summary_counts.total_open}</p>
        </article>
      </section>

      <section className={CH_CARD}>
        <p className={CH_SECTION_LABEL}>Top-urgent</p>
        <ul className="mt-3 space-y-2 text-sm">
          {data.top_urgent_items.map((item) => (
            <li key={`${item.source_type}:${item.source_id}:${item.title}`} className="rounded-lg border border-slate-200 p-3">
              <div className="flex items-center justify-between gap-2">
                <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${severityClass(item.severity)}`}>
                  {item.severity}
                </span>
                <span className="text-xs text-slate-500">
                  {item.due_at ? new Date(item.due_at).toLocaleString("de-DE") : "ohne Frist"}
                </span>
              </div>
              <p className="mt-2 font-medium text-slate-900">{item.title}</p>
              <p className="mt-1 text-xs text-slate-600">{item.summary_de}</p>
              <Link className="mt-2 inline-block text-xs font-semibold text-cyan-700 underline" href={item.action_href}>
                {item.action_label}
              </Link>
            </li>
          ))}
          {data.top_urgent_items.length === 0 ? (
            <li className="text-sm text-slate-500">Keine akuten Punkte.</li>
          ) : null}
        </ul>
      </section>

      {prepPack ? (
        <section className={CH_CARD}>
          <div className="mb-3 flex items-center justify-between">
            <p className={CH_SECTION_LABEL}>Authority & Audit Preparation Pack</p>
            <span className="text-xs text-slate-500">
              Fokus: {prepPack.focus} · {new Date(prepPack.generated_at_utc).toLocaleString("de-DE")}
            </span>
          </div>
          <PreparationPackPreview markdown={prepPack.markdown_de} />
        </section>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-2">
        {data.grouped_sections.map((group) => (
          <article key={group.section} className={CH_CARD}>
            <p className={CH_SECTION_LABEL}>{group.label_de}</p>
            <ul className="mt-3 space-y-2">
              {group.items.slice(0, 6).map((item) => (
                <li key={`${item.source_type}:${item.source_id}:${item.title}`} className="rounded border border-slate-200 px-3 py-2">
                  <p className="text-sm font-medium text-slate-900">{item.title}</p>
                  <p className="text-xs text-slate-600">{item.summary_de}</p>
                </li>
              ))}
              {group.items.length === 0 ? (
                <li className="text-xs text-slate-500">Keine offenen Punkte in diesem Bereich.</li>
              ) : null}
            </ul>
          </article>
        ))}
      </section>
    </div>
  );
}
