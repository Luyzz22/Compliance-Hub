import Link from "next/link";
import React from "react";

import { AiSystemsMutationsToolbar } from "@/components/tenant/AiSystemsMutationsToolbar";
import { AiSystemsRegistryTableClient } from "@/components/tenant/AiSystemsRegistryTableClient";
import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import { fetchTenantAISystems } from "@/lib/api";
import { CH_CARD, CH_PAGE_NAV_LINK, CH_SHELL } from "@/lib/boardLayout";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

type AISystem = {
  id: string;
  name: string;
  businessunit: string;
  risklevel: string;
  aiactcategory: string;
  status: string;
  owneremail?: string;
};

type PageProps = {
  searchParams?: Promise<{ ids?: string }> | { ids?: string };
};

export default async function TenantAISystemsPage({ searchParams }: PageProps) {
  const workspaceTenantId = await getWorkspaceTenantIdServer();
  const systems = (await fetchTenantAISystems()) as AISystem[];

  const sp =
    searchParams !== undefined ? await Promise.resolve(searchParams) : {};
  const idFilterRaw = typeof sp.ids === "string" ? sp.ids : "";
  const idSet = new Set(
    idFilterRaw
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean),
  );
  const filtered =
    idSet.size > 0 ? systems.filter((s) => idSet.has(s.id)) : systems;

  const total = filtered.length;
  const active = filtered.filter((s) => s.status === "active").length;
  const highRisk = filtered.filter((s) => s.risklevel === "high").length;

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Tenant"
        title="KI-System-Register"
        description="Zentrales Inventar aller KI-Systeme des Mandanten – Ausgangspunkt für Klassifizierung, NIS2-KPIs und Board-Reporting."
        actions={<AiSystemsMutationsToolbar tenantId={workspaceTenantId} />}
        below={
          <>
            <Link href="/tenant/eu-ai-act" className={CH_PAGE_NAV_LINK}>
              EU AI Act Cockpit
            </Link>
            <Link href="/tenant/compliance-overview" className={CH_PAGE_NAV_LINK}>
              Mandanten-Übersicht
            </Link>
          </>
        }
      />

      {idSet.size > 0 ? (
        <div
          role="status"
          className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-950"
        >
          Gefilterte Ansicht: {filtered.length} von {systems.length} Systemen (Deep-Link aus
          EU-AI-Act-Readiness).
        </div>
      ) : null}

      <section className="grid gap-4 md:grid-cols-3">
        <div className={CH_CARD}>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Gesamt
          </p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">{total}</p>
        </div>
        <div className={CH_CARD}>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Aktiv
          </p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-emerald-700">{active}</p>
        </div>
        <div className={CH_CARD}>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            High-Risk
          </p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-amber-700">{highRisk}</p>
        </div>
      </section>

      <section className={`${CH_CARD} overflow-hidden p-0`}>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--sbs-border)] px-5 py-3">
          <h2 className="text-sm font-bold text-[var(--sbs-text-primary)]">
            AI‑Systeme
          </h2>
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-xs text-[var(--sbs-text-secondary)]">
              {total} Einträge
              {idSet.size > 0 ? " (gefiltert)" : ""}
            </span>
          </div>
        </div>
        <AiSystemsRegistryTableClient
          systems={filtered}
          idFilterActive={idSet.size > 0}
          totalBeforeClientFilter={systems.length}
        />
      </section>
    </div>
  );
}
