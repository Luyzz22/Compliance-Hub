/**
 * Wave 50 – ERP-/SAP-Evidence-Hooks aus Portfolio + optionalem JSON-Store (rein funktional).
 */

import { daysSinceValidIso, isNonEmptyUnparsableIso } from "@/lib/mandantHistoryMerge";
import type {
  AdvisorEvidenceHooksMandantBlockDto,
  AdvisorEvidenceHooksPortfolioDto,
  AdvisorEvidenceHooksSummaryDto,
  AdvisorEvidenceHooksTopGapDto,
  EvidenceConnectionStatus,
  EvidenceDomain,
  EvidenceHookRowDto,
  EvidenceHookStoredRecord,
  EvidenceSourceSystemType,
} from "@/lib/advisorEvidenceHookTypes";
import { ADVISOR_EVIDENCE_HOOKS_VERSION } from "@/lib/advisorEvidenceHookTypes";
import type { KanzleiPortfolioPayload, KanzleiPortfolioRow } from "@/lib/kanzleiPortfolioTypes";

const DISCLAIMER_DE =
  "Metadaten-Hooks zur Enterprise-Readiness: keine Live-Anbindung an SAP, DATEV oder Dynamics. " +
  "Evidenz aus Mandanten-Historie (DATEV/Export) und manuell gepflegte Hooks – keine technische Vollintegration.";

/** Explizite, erklärbare Zuordnung Domäne → regulatorischer Kontext (DACH). */
export function evidenceDomainComplianceRelevanceDe(domain: EvidenceDomain): string[] {
  switch (domain) {
    case "invoice":
      return [
        "DSGVO: Verarbeitungskontext bei Beleg- und Rechnungsdaten",
        "GoBD: Aufzeichnungs- und Nachvollziehbarkeit (Belege)",
        "E-Rechnung EN 16931: Schnittstellen- und Exportevidenz",
      ];
    case "access":
      return [
        "NIS2 / KRITIS-Dach: Zugriffs- und Berechtigungsnachweise",
        "ISO 27001: Zutritts- und Zugriffssteuerung",
        "DSGVO Art. 32: TOM, Zugriffsschutz",
      ];
    case "approval":
      return [
        "GoBD / interne Kontrolle: Vier-Augen / Freigaben",
        "ISO 27001 / 42001: Steuerung sensibler Änderungen",
        "NIS2: Governance-Nachweise",
      ];
    case "vendor":
      return [
        "DSGVO: Auftragsverarbeitung, Lieferantenrisiko",
        "NIS2: Lieferketten-/Drittanbieter-Nachweise",
        "ISO 27001: Drittanbieter-Management",
      ];
    case "ai_system_inventory":
      return [
        "EU AI Act: Inventar und Risikoklassifikation",
        "ISO 42001: AI-Managementsystem, Lebenszyklus",
        "NIS2: Kritische Dienste und KI-Nutzung (Kontext)",
      ];
    case "policy_artifact":
      return [
        "ISO 42001 / 27001: Policies und Arbeitsanweisungen als Evidenz",
        "EU AI Act: Dokumentationspflichten (High-Risk-Kontext)",
        "DSGVO: Verzeichnis, TOM-Dokumentation",
      ];
    default: {
      const _x: never = domain;
      return [_x];
    }
  }
}

function datevSyntheticRow(
  row: KanzleiPortfolioRow,
  maxAgeDays: number,
  nowMs: number,
): EvidenceHookRowDto {
  const raw = row.last_datev_bundle_export_at;
  if (!raw?.trim()) {
    return {
      hook_id: `synthetic:datev:invoice:${row.tenant_id}`,
      tenant_id: row.tenant_id,
      source_system_type: "datev",
      source_label: "DATEV Export-Bundle (Historie)",
      evidence_domain: "invoice",
      connection_status: "not_connected",
      last_sync_at: null,
      evidence_hint_de:
        "Kein DATEV-Bundle-Export in der Mandanten-Historie erfasst. Kanzlei-Kanal: ZIP-Export als Evidenzanker neben Readiness-Export.",
      compliance_relevance_de: evidenceDomainComplianceRelevanceDe("invoice"),
      is_synthetic: true,
    };
  }
  if (isNonEmptyUnparsableIso(raw)) {
    return {
      hook_id: `synthetic:datev:invoice:${row.tenant_id}`,
      tenant_id: row.tenant_id,
      source_system_type: "datev",
      source_label: "DATEV Export-Bundle (Historie)",
      evidence_domain: "invoice",
      connection_status: "error",
      last_sync_at: raw,
      evidence_hint_de: "Letzter DATEV-Export-Zeitstempel nicht auswertbar – Historie prüfen.",
      compliance_relevance_de: evidenceDomainComplianceRelevanceDe("invoice"),
      is_synthetic: true,
    };
  }
  const days = daysSinceValidIso(raw, nowMs);
  if (days === null) {
    return {
      hook_id: `synthetic:datev:invoice:${row.tenant_id}`,
      tenant_id: row.tenant_id,
      source_system_type: "datev",
      source_label: "DATEV Export-Bundle (Historie)",
      evidence_domain: "invoice",
      connection_status: "error",
      last_sync_at: raw,
      evidence_hint_de: "Letzter DATEV-Export-Zeitstempel ungültig.",
      compliance_relevance_de: evidenceDomainComplianceRelevanceDe("invoice"),
      is_synthetic: true,
    };
  }
  if (days > maxAgeDays) {
    return {
      hook_id: `synthetic:datev:invoice:${row.tenant_id}`,
      tenant_id: row.tenant_id,
      source_system_type: "datev",
      source_label: "DATEV Export-Bundle (Historie)",
      evidence_domain: "invoice",
      connection_status: "planned",
      last_sync_at: raw,
      evidence_hint_de: `DATEV-Export älter als ${maxAgeDays} Tage – Kadenz mit Mandant abstimmen (GoBD/E-Rechnung-Kontext).`,
      compliance_relevance_de: evidenceDomainComplianceRelevanceDe("invoice"),
      is_synthetic: true,
    };
  }
  return {
    hook_id: `synthetic:datev:invoice:${row.tenant_id}`,
    tenant_id: row.tenant_id,
    source_system_type: "datev",
    source_label: "DATEV Export-Bundle (Historie)",
    evidence_domain: "invoice",
    connection_status: "connected",
    last_sync_at: raw,
    evidence_hint_de: "DATEV-Bundle-Export zuletzt innerhalb der Export-Kadenz erfasst.",
    compliance_relevance_de: evidenceDomainComplianceRelevanceDe("invoice"),
    is_synthetic: true,
  };
}

function hasStoredDatevInvoice(stored: EvidenceHookStoredRecord[], tenantId: string): boolean {
  return stored.some(
    (h) =>
      h.tenant_id === tenantId &&
      h.source_system_type === "datev" &&
      h.evidence_domain === "invoice",
  );
}

function hasSapFamilyStored(stored: EvidenceHookStoredRecord[], tenantId: string): boolean {
  return stored.some(
    (h) =>
      h.tenant_id === tenantId &&
      (h.source_system_type === "sap_s4hana" || h.source_system_type === "sap_btp"),
  );
}

function sapFamilyActiveInHooks(hooks: EvidenceHookRowDto[]): boolean {
  return hooks.some(
    (h) =>
      (h.source_system_type === "sap_s4hana" || h.source_system_type === "sap_btp") &&
      (h.connection_status === "connected" || h.connection_status === "planned"),
  );
}

function datevConnectedInHooks(hooks: EvidenceHookRowDto[]): boolean {
  return hooks.some((h) => h.source_system_type === "datev" && h.connection_status === "connected");
}

function storedToRow(h: EvidenceHookStoredRecord): EvidenceHookRowDto {
  const hint =
    h.note?.trim() ||
    `Manuell gepflegter Hook (${h.source_label}). Status: ${h.connection_status}.`;
  return {
    hook_id: h.hook_id,
    tenant_id: h.tenant_id,
    source_system_type: h.source_system_type,
    source_label: h.source_label,
    evidence_domain: h.evidence_domain,
    connection_status: h.connection_status,
    last_sync_at: h.last_sync_at,
    evidence_hint_de: hint,
    compliance_relevance_de: evidenceDomainComplianceRelevanceDe(h.evidence_domain),
    is_synthetic: false,
  };
}

function mandantHintDe(block: AdvisorEvidenceHooksMandantBlockDto): string {
  const sapActive = sapFamilyActiveInHooks(block.hooks);
  const datevOk = datevConnectedInHooks(block.hooks);
  const parts: string[] = [];
  if (sapActive) parts.push("SAP/BTP-Evidenz-Hook als verbunden oder geplant erfasst.");
  else parts.push("Kein aktiver SAP-/BTP-Hook – typische Enterprise-Lücke für Industrie-Mittelstand.");
  if (datevOk) parts.push("DATEV-Bundle-Evidenz innerhalb Kadenz.");
  else parts.push("DATEV-Bundle fehlt oder Kadenz offen – Kanzlei-Fokus.");
  return parts.join(" ");
}

function buildMarkdownDe(dto: AdvisorEvidenceHooksPortfolioDto): string {
  const s = dto.summary;
  const lines: string[] = [];
  lines.push("# Enterprise Evidence Hooks (Portfolio)");
  lines.push("");
  lines.push(`_${dto.disclaimer_de}_`);
  lines.push("");
  lines.push(`Erzeugt: ${new Date(dto.generated_at).toLocaleString("de-DE")} · Schema ${dto.version}`);
  lines.push("");
  lines.push("## Kurzüberblick");
  lines.push(`- Hook-Zeilen gesamt: **${s.total_hook_rows}**`);
  lines.push(
    `- Status: verbunden **${s.by_status.connected}**, geplant **${s.by_status.planned}**, nicht verbunden **${s.by_status.not_connected}**, Fehler **${s.by_status.error}**`,
  );
  lines.push(`- Mandanten ohne SAP/BTP-Touchpoint (verbunden/geplant): **${s.mandanten_without_sap_touchpoint}**`);
  lines.push(`- Mandanten ohne DATEV-Export in Historie: **${s.mandanten_without_datev_export}**`);
  lines.push(`- Upsell-Kandidaten (Enterprise-Lücke + Drucksignal): **${s.mandanten_enterprise_upsell_candidates}**`);
  lines.push("");
  lines.push("## Top Lücken");
  for (const g of dto.top_gaps.slice(0, 8)) {
    const name = g.mandant_label ?? g.tenant_id;
    lines.push(`- **${name}** (\`${g.tenant_id}\`): ${g.hint_de}`);
  }
  lines.push("");
  lines.push("## DATEV vs. ERP");
  lines.push(
    "- DATEV-Bundle deckt den Kanzlei-Kanal; SAP/ERP-Hooks adressieren Industrie-Mittelstand und Enterprise-Landschaften.",
  );
  lines.push(
    "- Beides ergänzt sich: strukturierter Readiness-/DATEV-Export in ComplianceHub plus spätere Systemevidenz.",
  );
  lines.push("");
  return lines.join("\n");
}

export function buildAdvisorEvidenceHooksPortfolioDto(
  payload: KanzleiPortfolioPayload,
  stored: EvidenceHookStoredRecord[],
  opts?: { generatedAt?: Date; nowMs?: number },
): AdvisorEvidenceHooksPortfolioDto {
  const generatedAt = opts?.generatedAt ?? new Date();
  const nowMs = opts?.nowMs ?? generatedAt.getTime();
  const maxAge = payload.constants.any_export_max_age_days;

  const byTenantStored = new Map<string, EvidenceHookStoredRecord[]>();
  for (const h of stored) {
    const list = byTenantStored.get(h.tenant_id) ?? [];
    list.push(h);
    byTenantStored.set(h.tenant_id, list);
  }

  const mandanten: AdvisorEvidenceHooksMandantBlockDto[] = [];
  let mandantenWithoutDatevExport = 0;
  let mandantenWithoutSapTouchpoint = 0;
  let upsellCandidates = 0;

  for (const row of payload.rows) {
    const tid = row.tenant_id;
    const tenantStored = byTenantStored.get(tid) ?? [];
    const hooks: EvidenceHookRowDto[] = tenantStored.map(storedToRow);

    if (!hasStoredDatevInvoice(stored, tid)) {
      hooks.push(datevSyntheticRow(row, maxAge, nowMs));
    }

    if (!hasSapFamilyStored(stored, tid)) {
      hooks.push({
        hook_id: `synthetic:sap_s4hana:invoice:${tid}`,
        tenant_id: tid,
        source_system_type: "sap_s4hana",
        source_label: "SAP S/4HANA / ERP-Landschaft (Evidenz-Platzhalter)",
        evidence_domain: "invoice",
        connection_status: "not_connected",
        last_sync_at: null,
        evidence_hint_de:
          "Kein SAP- oder BTP-Hook erfasst. Für viele Mittelständler zentrale Beleg-/Buchungsevidenz – später z. B. über SAP BTP anbindbar.",
        compliance_relevance_de: evidenceDomainComplianceRelevanceDe("invoice"),
        is_synthetic: true,
      });
    }

    const block: AdvisorEvidenceHooksMandantBlockDto = {
      tenant_id: tid,
      mandant_label: row.mandant_label,
      hooks,
      enterprise_readiness_hint_de: "",
      links: row.links,
    };
    block.enterprise_readiness_hint_de = mandantHintDe(block);
    mandanten.push(block);

    if (!row.last_datev_bundle_export_at?.trim()) mandantenWithoutDatevExport += 1;

    if (!sapFamilyActiveInHooks(hooks)) mandantenWithoutSapTouchpoint += 1;

    const upsell =
      !sapFamilyActiveInHooks(hooks) &&
      (row.readiness_class === "advanced_governance" || row.readiness_class === "baseline_governance") &&
      (row.never_any_export ||
        row.any_export_stale ||
        row.open_points_count >= payload.constants.many_open_points_threshold);
    if (upsell) upsellCandidates += 1;
  }

  const by_status: Record<EvidenceConnectionStatus, number> = {
    not_connected: 0,
    planned: 0,
    connected: 0,
    error: 0,
  };
  const by_source: Partial<Record<EvidenceSourceSystemType, number>> = {};
  for (const m of mandanten) {
    for (const h of m.hooks) {
      by_status[h.connection_status] += 1;
      by_source[h.source_system_type] = (by_source[h.source_system_type] ?? 0) + 1;
    }
  }

  const totalRows = mandanten.reduce((acc, m) => acc + m.hooks.length, 0);

  const summary: AdvisorEvidenceHooksSummaryDto = {
    total_hook_rows: totalRows,
    by_status,
    by_source_type: by_source,
    mandanten_without_sap_touchpoint: mandantenWithoutSapTouchpoint,
    mandanten_without_datev_export: mandantenWithoutDatevExport,
    mandanten_enterprise_upsell_candidates: upsellCandidates,
  };

  const gapScores = mandanten.map((m) => {
    let score = 0;
    if (!datevConnectedInHooks(m.hooks)) score += 2;
    if (!sapFamilyActiveInHooks(m.hooks)) score += 2;
    if (m.hooks.some((h) => h.connection_status === "error")) score += 3;
    const row = payload.rows.find((r) => r.tenant_id === m.tenant_id);
    if (row?.never_any_export) score += 1;
    return { m, score };
  });
  gapScores.sort((a, b) => b.score - a.score);
  const top_gaps: AdvisorEvidenceHooksTopGapDto[] = gapScores.slice(0, 8).map(({ m }) => ({
    tenant_id: m.tenant_id,
    mandant_label: m.mandant_label,
    hint_de: m.enterprise_readiness_hint_de,
    links: m.links,
  }));

  const dto: AdvisorEvidenceHooksPortfolioDto = {
    version: ADVISOR_EVIDENCE_HOOKS_VERSION,
    generated_at: generatedAt.toISOString(),
    portfolio_generated_at: payload.generated_at,
    disclaimer_de: DISCLAIMER_DE,
    summary,
    mandanten,
    top_gaps,
    markdown_de: "",
  };
  dto.markdown_de = buildMarkdownDe(dto);
  return dto;
}
