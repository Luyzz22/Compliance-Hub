import { describe, expect, it } from "vitest";

import type { TenantIncidentDrilldownOutDto } from "@/lib/api";

import {
  applyDrilldownFilters,
  isAvailabilityDominant,
  isSafetyDominant,
  mapTenantDrilldownDtoToAdvisorOut,
  matchesSupplierFilter,
  sortDrilldownItems,
  type AdvisorIncidentDrilldownItem,
} from "./advisorIncidentDrilldownModel";

function item(p: Partial<AdvisorIncidentDrilldownItem>): AdvisorIncidentDrilldownItem {
  return {
    aiSystemId: p.aiSystemId ?? "id",
    aiSystemName: p.aiSystemName ?? "Name",
    supplierSourceLabelDe: p.supplierSourceLabelDe ?? "SAP AI Core",
    eventSource: p.eventSource ?? "sap_ai_core",
    incidentCountTotal: p.incidentCountTotal ?? 0,
    incidentCountByCategory: p.incidentCountByCategory ?? { safety: 0, availability: 0, other: 0 },
    weightedShareSafety: p.weightedShareSafety ?? 0,
    weightedShareAvailability: p.weightedShareAvailability ?? 0,
    weightedShareOther: p.weightedShareOther ?? 0,
    localOamiHintDe: p.localOamiHintDe ?? "",
  };
}

describe("mapTenantDrilldownDtoToAdvisorOut", () => {
  it("maps snake_case DTO to camelCase view model", () => {
    const dto: TenantIncidentDrilldownOutDto = {
      tenant_id: "t-1",
      window_days: 90,
      systems_with_runtime_events: 4,
      systems_with_incidents: 2,
      items: [
        {
          ai_system_id: "as-1",
          ai_system_name: "Bot A",
          supplier_label_de: "SAP AI Core",
          event_source: "sap_ai_core",
          incident_total_90d: 3,
          incident_count_by_category: { safety: 2, availability: 1, other: 0 },
          weighted_incident_share_safety: 0.55,
          weighted_incident_share_availability: 0.3,
          weighted_incident_share_other: 0.15,
          oami_local_hint_de: "Sicherheitsnahe Signale überwiegen.",
        },
      ],
    };
    const out = mapTenantDrilldownDtoToAdvisorOut(dto, "2026-03-29T12:00:00.000Z");
    expect(out.tenantId).toBe("t-1");
    expect(out.windowDays).toBe(90);
    expect(out.generatedAt).toBe("2026-03-29T12:00:00.000Z");
    expect(out.items[0]).toMatchObject({
      aiSystemId: "as-1",
      aiSystemName: "Bot A",
      supplierSourceLabelDe: "SAP AI Core",
      eventSource: "sap_ai_core",
      incidentCountTotal: 3,
      incidentCountByCategory: { safety: 2, availability: 1, other: 0 },
      weightedShareSafety: 0.55,
      weightedShareAvailability: 0.3,
      weightedShareOther: 0.15,
      localOamiHintDe: "Sicherheitsnahe Signale überwiegen.",
    });
  });
});

describe("dominance & filters", () => {
  it("isSafetyDominant when safety share >= 0.45 and strictly highest", () => {
    expect(isSafetyDominant(item({ weightedShareSafety: 0.45, weightedShareAvailability: 0.3, weightedShareOther: 0.25 }))).toBe(true);
    expect(isSafetyDominant(item({ weightedShareSafety: 0.44, weightedShareAvailability: 0.3, weightedShareOther: 0.26 }))).toBe(false);
    expect(isSafetyDominant(item({ weightedShareSafety: 0.5, weightedShareAvailability: 0.5, weightedShareOther: 0 }))).toBe(false);
  });

  it("isAvailabilityDominant mirrors safety rule", () => {
    expect(isAvailabilityDominant(item({ weightedShareSafety: 0.2, weightedShareAvailability: 0.5, weightedShareOther: 0.3 }))).toBe(true);
  });

  it("matchesSupplierFilter for sap_ai_core and other", () => {
    const sap = item({ eventSource: "sap_ai_core" });
    const custom = item({ eventSource: "manual_import" });
    expect(matchesSupplierFilter(sap, "sap_ai_core")).toBe(true);
    expect(matchesSupplierFilter(custom, "sap_ai_core")).toBe(false);
    expect(matchesSupplierFilter(sap, "other")).toBe(false);
    expect(matchesSupplierFilter(custom, "other")).toBe(false);
    expect(matchesSupplierFilter(item({ eventSource: "weird" }), "other")).toBe(true);
  });
});

describe("sortDrilldownItems & applyDrilldownFilters", () => {
  it("sorts by incident total desc, then safety share desc", () => {
    const a = item({ aiSystemId: "a", aiSystemName: "A", incidentCountTotal: 5, weightedShareSafety: 0.4 });
    const b = item({ aiSystemId: "b", aiSystemName: "B", incidentCountTotal: 10, weightedShareSafety: 0.2 });
    const c = item({ aiSystemId: "c", aiSystemName: "C", incidentCountTotal: 10, weightedShareSafety: 0.6 });
    const sorted = sortDrilldownItems([a, b, c]);
    expect(sorted.map((x) => x.aiSystemId)).toEqual(["c", "b", "a"]);
  });

  it("applyDrilldownFilters filters by supplier and focus then sorts", () => {
    const rows = [
      item({
        aiSystemId: "1",
        aiSystemName: "S1",
        eventSource: "sap_ai_core",
        incidentCountTotal: 8,
        weightedShareSafety: 0.5,
        weightedShareAvailability: 0.25,
        weightedShareOther: 0.25,
      }),
      item({
        aiSystemId: "2",
        aiSystemName: "S2",
        eventSource: "manual_import",
        incidentCountTotal: 20,
        weightedShareSafety: 0.2,
        weightedShareAvailability: 0.5,
        weightedShareOther: 0.3,
      }),
    ];
    const safetyOnly = applyDrilldownFilters(rows, "all", "safety_dominant");
    expect(safetyOnly).toHaveLength(1);
    expect(safetyOnly[0].aiSystemId).toBe("1");

    const sapOnly = applyDrilldownFilters(rows, "sap_ai_core", "all");
    expect(sapOnly).toHaveLength(1);
    expect(sapOnly[0].aiSystemId).toBe("1");
  });
});
