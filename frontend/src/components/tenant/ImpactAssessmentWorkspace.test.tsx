import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type {
  AIImpactAssessmentPortfolioResponseDto,
  ImpactSectionKeyDto,
} from "@/lib/api";

import { ImpactAssessmentWorkspace } from "./ImpactAssessmentWorkspace";

const mockFetch = vi.fn();
const mockUpdate = vi.fn();

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    fetchAIImpactAssessmentPortfolio: (...args: unknown[]) => mockFetch(...args),
    updateAIImpactAssessment: (...args: unknown[]) => mockUpdate(...args),
  };
});

const sectionKeys: ImpactSectionKeyDto[] = [
  "processing_description_and_purpose",
  "necessity_and_proportionality",
  "deployment_period_and_frequency",
  "affected_persons_and_groups",
  "rights_and_freedoms_risks",
  "safeguards_security_and_mitigations",
  "human_oversight_and_governance",
  "incident_complaint_and_redress",
];

function fixture(version = 0): AIImpactAssessmentPortfolioResponseDto {
  return {
    tenant_id: "tenant-1",
    generated_at_utc: "2026-08-11T08:00:00Z",
    readiness_score_pct: 0,
    posture: "scope_incomplete",
    framework_version: "gdpr-35-36-eu-ai-act-27-v1",
    source_urls: {
      gdpr: "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
      eu_ai_act: "https://eur-lex.europa.eu/eli/reg/2024/1689/oj",
    },
    legal_disclaimer_de: "Keine automatische Pflichtfeststellung und keine automatische Einsatzfreigabe.",
    summary: {
      total_systems: 1,
      assessed_systems: version > 0 ? 1 : 0,
      scope_open_count: 1,
      in_review_count: 0,
      approved_count: 0,
      high_residual_risk_count: 0,
      consultation_open_count: 0,
      overdue_review_count: 0,
    },
    systems: [
      {
        ai_system_id: "sys-1",
        ai_system_name: "Bürger-Service Assistent",
        business_unit: "Digital Service",
        risk_level: "high",
        ai_act_category: "high_risk",
        registry_dpia_signal: true,
        readiness_score_pct: 0,
        posture: "scope_incomplete",
        blockers: ["DSFA-Scope ist nicht entschieden", "FRIA-Scope ist nicht entschieden"],
        applicable_sections: 8,
        reviewed_sections: 0,
        review_overdue: false,
        assessment: {
          id: version > 0 ? "impact-1" : null,
          tenant_id: "tenant-1",
          ai_system_id: "sys-1",
          dpia_scope: "undetermined",
          fria_scope: "undetermined",
          deployer_context: "unknown",
          scope_rationale: null,
          lifecycle_status: "draft",
          residual_risk: "unknown",
          assessment_owner: null,
          independent_reviewer: null,
          dpo_involved: false,
          stakeholder_views_status: "not_assessed",
          prior_consultation_status: "not_assessed",
          prior_consultation_reference: null,
          reviewed_at_utc: null,
          approved_at_utc: null,
          review_due_at_utc: null,
          version,
          created_at_utc: null,
          updated_at_utc: null,
          updated_by: null,
          sections: sectionKeys.map((sectionKey, index) => ({
            section_key: sectionKey,
            status: "not_started",
            summary: null,
            evidence_reference: null,
            rationale: null,
            title_de: `Prüffeld ${index + 1}`,
            description_de: "Prüfbare Beschreibung des Auswirkungsfeldes.",
            legal_basis: index < 2 ? "DSGVO Art. 35" : "EU AI Act Art. 27",
            updated_at_utc: null,
          })),
        },
      },
    ],
  };
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ImpactAssessmentWorkspace", () => {
  it("renders the decision path, blockers, all sections and the legal boundary", () => {
    render(<ImpactAssessmentWorkspace tenantId="tenant-1" initialData={fixture()} />);

    expect(screen.getByRole("heading", { name: /Vom Scope zur verantworteten Freigabe/i })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Bürger-Service Assistent" })).toBeTruthy();
    expect(screen.getByText("DSFA-Scope ist nicht entschieden")).toBeTruthy();
    expect(screen.getAllByLabelText("Prüffeldstatus")).toHaveLength(8);
    expect(screen.getByText(/Keine automatische Pflichtfeststellung/i)).toBeTruthy();
  });

  it("blocks reviewed sections without summary and evidence before the API call", async () => {
    render(<ImpactAssessmentWorkspace tenantId="tenant-1" initialData={fixture()} />);

    fireEvent.change(screen.getAllByLabelText("Prüffeldstatus")[0], {
      target: { value: "reviewed" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Assessment speichern" }));

    expect((await screen.findByRole("alert")).textContent).toMatch(/Zusammenfassung und Evidenzreferenz/i);
    expect(mockUpdate).not.toHaveBeenCalled();
  });

  it("requires a rationale for a not-required scope decision", async () => {
    render(<ImpactAssessmentWorkspace tenantId="tenant-1" initialData={fixture()} />);

    fireEvent.change(screen.getByLabelText("DSFA-Scope"), {
      target: { value: "not_required" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Assessment speichern" }));

    expect((await screen.findByRole("alert")).textContent).toMatch(/Scope-Begründung/i);
    expect(mockUpdate).not.toHaveBeenCalled();
  });

  it("prevents approval while scope and independent review remain incomplete", async () => {
    render(<ImpactAssessmentWorkspace tenantId="tenant-1" initialData={fixture()} />);

    fireEvent.change(screen.getByLabelText("Lifecycle"), {
      target: { value: "approved" },
    });
    fireEvent.change(screen.getByLabelText("Assessment Owner (Funktionsrolle)"), {
      target: { value: "Privacy Control" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Assessment speichern" }));

    expect((await screen.findByRole("alert")).textContent).toMatch(/DSFA- und FRIA-Scope/i);
    expect(mockUpdate).not.toHaveBeenCalled();
  });

  it("persists all eight sections with optimistic version and refreshes the portfolio", async () => {
    mockUpdate.mockResolvedValue(fixture(1).systems[0].assessment);
    mockFetch.mockResolvedValue(fixture(1));
    render(<ImpactAssessmentWorkspace tenantId="tenant-1" initialData={fixture()} />);

    fireEvent.click(screen.getByRole("button", { name: "Assessment speichern" }));

    await waitFor(() => expect(mockUpdate).toHaveBeenCalledTimes(1));
    expect(mockUpdate).toHaveBeenCalledWith(
      "tenant-1",
      "sys-1",
      expect.objectContaining({
        expected_version: 0,
        lifecycle_status: "draft",
        sections: expect.arrayContaining([
          expect.objectContaining({ section_key: "rights_and_freedoms_risks" }),
        ]),
      }),
    );
    expect(mockUpdate.mock.calls[0][2].sections).toHaveLength(8);
    await waitFor(() => expect(mockFetch).toHaveBeenCalledWith("tenant-1"));
  });
});
