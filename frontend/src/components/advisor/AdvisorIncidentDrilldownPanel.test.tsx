import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { TenantIncidentDrilldownOutDto } from "@/lib/api";

import { AdvisorIncidentDrilldownPanel } from "./AdvisorIncidentDrilldownPanel";

const governanceMaturity = vi.hoisted(() => vi.fn(() => true));

vi.mock("@/lib/config", () => ({
  featureGovernanceMaturity: governanceMaturity,
}));

const fetchDrilldown = vi.hoisted(() => vi.fn());
const fetchCsv = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    fetchAdvisorTenantIncidentDrilldown: fetchDrilldown,
    fetchAdvisorTenantIncidentDrilldownCsvBlob: fetchCsv,
  };
});

function dtoWithItems(items: TenantIncidentDrilldownOutDto["items"]): TenantIncidentDrilldownOutDto {
  return {
    tenant_id: "tenant-x",
    window_days: 90,
    systems_with_runtime_events: items.length,
    systems_with_incidents: items.length,
    items,
  };
}

const twoItemsDto = dtoWithItems([
  {
    ai_system_id: "sys-high",
    ai_system_name: "System Viel",
    supplier_label_de: "SAP AI Core",
    event_source: "sap_ai_core",
    incident_total_90d: 12,
    incident_count_by_category: { safety: 8, availability: 2, other: 2 },
    weighted_incident_share_safety: 0.55,
    weighted_incident_share_availability: 0.25,
    weighted_incident_share_other: 0.2,
    oami_local_hint_de: "Safety-Schwerpunkt.",
  },
  {
    ai_system_id: "sys-low",
    ai_system_name: "System Wenig",
    supplier_label_de: "Manuell / Custom",
    event_source: "manual_import",
    incident_total_90d: 3,
    incident_count_by_category: { safety: 0, availability: 2, other: 1 },
    weighted_incident_share_safety: 0.15,
    weighted_incident_share_availability: 0.55,
    weighted_incident_share_other: 0.3,
    oami_local_hint_de: "Verfügbarkeit dominiert.",
  },
]);

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  governanceMaturity.mockReturnValue(true);
});

describe("AdvisorIncidentDrilldownPanel", () => {
  it("hides section when backend returns no drilldown items", async () => {
    fetchDrilldown.mockResolvedValue(dtoWithItems([]));
    render(<AdvisorIncidentDrilldownPanel advisorId="adv@x" clientTenantId="t-1" variant="snapshot" />);
    await waitFor(() => {
      expect(screen.queryByTestId("advisor-incident-drilldown-loading")).toBeNull();
    });
    expect(screen.queryByTestId("advisor-incident-drilldown-section")).toBeNull();
  });

  it("renders table rows from mocked drilldown and default sort (highest total first)", async () => {
    fetchDrilldown.mockResolvedValue(twoItemsDto);
    render(<AdvisorIncidentDrilldownPanel advisorId="adv@x" clientTenantId="t-1" variant="snapshot" />);
    await waitFor(() => {
      expect(screen.getByTestId("advisor-incident-drilldown-section")).toBeTruthy();
    });
    expect(screen.getByText("Incidents nach KI-System und Lieferant")).toBeTruthy();
    expect(screen.getByText("90-Tage-Überblick zu Laufzeit-Incidents und OAMI-Treibern.")).toBeTruthy();
    const rows = screen.getAllByRole("row");
    const bodyRows = rows.slice(1);
    expect(bodyRows).toHaveLength(2);
    expect(within(bodyRows[0]).getByText("System Viel")).toBeTruthy();
    expect(within(bodyRows[1]).getByText("System Wenig")).toBeTruthy();
  });

  it("filters by supplier and shows empty-filter message when no match", async () => {
    fetchDrilldown.mockResolvedValue(twoItemsDto);
    render(<AdvisorIncidentDrilldownPanel advisorId="adv@x" clientTenantId="t-1" variant="snapshot" />);
    await waitFor(() => screen.getByTestId("advisor-incident-drilldown-section"));
    const supplierSelect = screen.getByTestId("advisor-drilldown-filter-supplier");
    fireEvent.change(supplierSelect, { target: { value: "sap_ai_core" } });
    await waitFor(() => {
      expect(screen.getByText("System Viel")).toBeTruthy();
      expect(screen.queryByText("System Wenig")).toBeNull();
    });
    fireEvent.change(supplierSelect, { target: { value: "sap_btp_event_mesh" } });
    await waitFor(() => {
      expect(screen.getByTestId("advisor-drilldown-empty-filter")).toBeTruthy();
    });
  });

  it("filters by OAMI focus (safety-dominant)", async () => {
    fetchDrilldown.mockResolvedValue(twoItemsDto);
    render(<AdvisorIncidentDrilldownPanel advisorId="adv@x" clientTenantId="t-1" variant="snapshot" />);
    await waitFor(() => screen.getByTestId("advisor-incident-drilldown-section"));
    fireEvent.change(screen.getByTestId("advisor-drilldown-filter-focus"), {
      target: { value: "safety_dominant" },
    });
    await waitFor(() => {
      expect(screen.getByText("System Viel")).toBeTruthy();
      expect(screen.queryByText("System Wenig")).toBeNull();
    });
  });

  it("returns null when governance maturity feature is off", () => {
    governanceMaturity.mockReturnValue(false);
    const { container } = render(
      <AdvisorIncidentDrilldownPanel advisorId="adv@x" clientTenantId="t-1" variant="snapshot" />,
    );
    expect(container.firstChild).toBeNull();
    expect(fetchDrilldown).not.toHaveBeenCalled();
  });

  it("full variant shows Export CSV", async () => {
    fetchDrilldown.mockResolvedValue(twoItemsDto);
    render(<AdvisorIncidentDrilldownPanel advisorId="adv@x" clientTenantId="t-1" variant="full" />);
    await waitFor(() => screen.getByTestId("advisor-incident-drilldown-full"));
    expect(screen.getByTestId("advisor-drilldown-export-csv")).toBeTruthy();
  });
});
