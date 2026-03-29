/**
 * View-Model für Advisor Incident-Drilldown (camelCase, von API snake_case gemappt).
 */

import type { TenantIncidentDrilldownItemDto, TenantIncidentDrilldownOutDto } from "@/lib/api";

export interface AdvisorIncidentDrilldownItem {
  aiSystemId: string;
  aiSystemName: string;
  supplierSourceLabelDe: string;
  eventSource: string;
  incidentCountTotal: number;
  incidentCountByCategory: {
    safety: number;
    availability: number;
    other: number;
  };
  weightedShareSafety: number;
  weightedShareAvailability: number;
  weightedShareOther: number;
  localOamiHintDe: string;
}

export interface AdvisorIncidentDrilldownOut {
  tenantId: string;
  windowDays: number;
  /** ISO-Zeitpunkt des Client-Fetch (API liefert kein separates generated_at). */
  generatedAt: string;
  systemsWithRuntimeEvents: number;
  systemsWithIncidents: number;
  items: AdvisorIncidentDrilldownItem[];
}

export type SupplierFilterId = "all" | "sap_ai_core" | "sap_btp_event_mesh" | "manual_import" | "other";

export type CategoryFocusFilterId = "all" | "safety_dominant" | "availability_dominant" | "balanced_low";

const DOMINANCE = 0.45;

export function mapTenantDrilldownDtoToAdvisorOut(
  dto: TenantIncidentDrilldownOutDto,
  generatedAtIso: string,
): AdvisorIncidentDrilldownOut {
  return {
    tenantId: dto.tenant_id,
    windowDays: dto.window_days,
    generatedAt: generatedAtIso,
    systemsWithRuntimeEvents: dto.systems_with_runtime_events,
    systemsWithIncidents: dto.systems_with_incidents,
    items: dto.items.map(mapItem),
  };
}

function mapItem(it: TenantIncidentDrilldownItemDto): AdvisorIncidentDrilldownItem {
  return {
    aiSystemId: it.ai_system_id,
    aiSystemName: it.ai_system_name,
    supplierSourceLabelDe: it.supplier_label_de,
    eventSource: it.event_source,
    incidentCountTotal: it.incident_total_90d,
    incidentCountByCategory: { ...it.incident_count_by_category },
    weightedShareSafety: it.weighted_incident_share_safety,
    weightedShareAvailability: it.weighted_incident_share_availability,
    weightedShareOther: it.weighted_incident_share_other,
    localOamiHintDe: it.oami_local_hint_de,
  };
}

export function isSafetyDominant(it: AdvisorIncidentDrilldownItem): boolean {
  const { weightedShareSafety: s, weightedShareAvailability: a, weightedShareOther: o } = it;
  return s >= DOMINANCE && s > a && s > o;
}

export function isAvailabilityDominant(it: AdvisorIncidentDrilldownItem): boolean {
  const { weightedShareSafety: s, weightedShareAvailability: a, weightedShareOther: o } = it;
  return a >= DOMINANCE && a > s && a > o;
}

export function isBalancedOrLow(it: AdvisorIncidentDrilldownItem): boolean {
  if (it.incidentCountTotal <= 3) {
    return true;
  }
  return !isSafetyDominant(it) && !isAvailabilityDominant(it);
}

export function matchesSupplierFilter(
  it: AdvisorIncidentDrilldownItem,
  filter: SupplierFilterId,
): boolean {
  if (filter === "all") {
    return true;
  }
  const es = (it.eventSource || "").toLowerCase();
  if (filter === "other") {
    return !["sap_ai_core", "sap_btp_event_mesh", "manual_import"].includes(es);
  }
  return es === filter;
}

export function matchesCategoryFocusFilter(
  it: AdvisorIncidentDrilldownItem,
  filter: CategoryFocusFilterId,
): boolean {
  if (filter === "all") {
    return true;
  }
  if (filter === "safety_dominant") {
    return isSafetyDominant(it);
  }
  if (filter === "availability_dominant") {
    return isAvailabilityDominant(it);
  }
  return isBalancedOrLow(it);
}

/** Standardsortierung: meiste Incidents zuerst, dann höchster Safety-Anteil. */
export function sortDrilldownItems(items: AdvisorIncidentDrilldownItem[]): AdvisorIncidentDrilldownItem[] {
  return [...items].sort((a, b) => {
    if (b.incidentCountTotal !== a.incidentCountTotal) {
      return b.incidentCountTotal - a.incidentCountTotal;
    }
    if (b.weightedShareSafety !== a.weightedShareSafety) {
      return b.weightedShareSafety - a.weightedShareSafety;
    }
    return a.aiSystemName.localeCompare(b.aiSystemName, "de");
  });
}

export function applyDrilldownFilters(
  items: AdvisorIncidentDrilldownItem[],
  supplier: SupplierFilterId,
  focus: CategoryFocusFilterId,
): AdvisorIncidentDrilldownItem[] {
  return sortDrilldownItems(
    items.filter((it) => matchesSupplierFilter(it, supplier) && matchesCategoryFocusFilter(it, focus)),
  );
}

export const SUPPLIER_FILTER_OPTIONS: { id: SupplierFilterId; label: string }[] = [
  { id: "all", label: "Alle Lieferanten" },
  { id: "sap_ai_core", label: "SAP AI Core" },
  { id: "sap_btp_event_mesh", label: "SAP BTP Event Mesh" },
  { id: "manual_import", label: "Manuell / Custom" },
  { id: "other", label: "Sonstige" },
];

export const CATEGORY_FOCUS_OPTIONS: { id: CategoryFocusFilterId; label: string }[] = [
  { id: "all", label: "Alle Fokus-Typen" },
  { id: "safety_dominant", label: "Safety-dominant" },
  { id: "availability_dominant", label: "Verfügbarkeit-dominant" },
  { id: "balanced_low", label: "Ausgewogen / wenige Fälle" },
];
