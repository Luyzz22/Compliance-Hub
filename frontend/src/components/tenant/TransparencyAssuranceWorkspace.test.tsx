import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type {
  AITransparencyAssuranceResponseDto,
  TransparencyControlKeyDto,
} from "@/lib/api";

import { TransparencyAssuranceWorkspace } from "./TransparencyAssuranceWorkspace";

const mockFetch = vi.fn();
const mockUpdate = vi.fn();

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    fetchAITransparencyAssurance: (...args: unknown[]) => mockFetch(...args),
    updateAITransparencyAssessment: (...args: unknown[]) => mockUpdate(...args),
  };
});

const keys: TransparencyControlKeyDto[] = [
  "ai_interaction_disclosure",
  "synthetic_content_marking",
  "emotion_biometric_notice",
  "deepfake_disclosure",
  "public_interest_text_review_or_disclosure",
  "gdpr_transparency_notice",
];

function fixture(version = 0): AITransparencyAssuranceResponseDto {
  return {
    tenant_id: "tenant-1",
    generated_at_utc: "2026-07-21T10:00:00Z",
    article_50_application_at_utc: "2026-08-02T00:00:00Z",
    days_until_application: 12,
    readiness_score_pct: 0,
    posture: "scope_incomplete",
    framework_version: "ec-article-50-guidelines-2026-07-20",
    source_url: "https://digital-strategy.ec.europa.eu/example",
    legal_disclaimer_de: "Keine automatische Konformitätsfeststellung.",
    summary: {
      total_systems: 1,
      assessed_systems: version > 0 ? 1 : 0,
      requires_scope_count: 1,
      verified_systems: 0,
      overdue_review_count: 0,
      applicable_controls: 6,
      verified_controls: 0,
    },
    systems: [
      {
        ai_system_id: "sys-1",
        ai_system_name: "Customer Service Assistant",
        business_unit: "Service",
        risk_level: "limited",
        ai_act_category: "limited_risk",
        readiness_score_pct: 0,
        posture: "requires_scope",
        applicable_controls: 6,
        verified_controls: 0,
        review_overdue: false,
        assessment: {
          id: version > 0 ? "assessment-1" : null,
          tenant_id: "tenant-1",
          ai_system_id: "sys-1",
          role_scope: "unknown",
          control_owner: null,
          reviewer: null,
          reviewed_at_utc: null,
          review_due_at_utc: null,
          version,
          created_at_utc: null,
          updated_at_utc: null,
          updated_by: null,
          controls: keys.map((controlKey) => ({
            control_key: controlKey,
            status: "not_assessed",
            evidence_reference: null,
            rationale: null,
            title_de: `Kontrolle ${controlKey}`,
            description_de: "Prüfbare Beschreibung",
            legal_basis: controlKey === "gdpr_transparency_notice" ? "DSGVO Art. 12–14" : "EU AI Act Art. 50",
            accountable_role: "Provider",
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

describe("TransparencyAssuranceWorkspace", () => {
  it("renders the deadline, system evidence controls and legal boundary", () => {
    render(<TransparencyAssuranceWorkspace tenantId="tenant-1" initialData={fixture()} />);

    expect(screen.getByRole("heading", { name: /Art\. 50 Transparenzpflichten/i })).toBeTruthy();
    expect(screen.getByText(/in 12 Tagen anwendbar/i)).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Customer Service Assistant" })).toBeTruthy();
    expect(screen.getAllByLabelText("Kontrollstatus")).toHaveLength(6);
    expect(screen.getByText("Keine automatische Konformitätsfeststellung.")).toBeTruthy();
  });

  it("blocks a verified status without evidence before calling the API", async () => {
    render(<TransparencyAssuranceWorkspace tenantId="tenant-1" initialData={fixture()} />);

    fireEvent.change(screen.getAllByLabelText("Kontrollstatus")[0], {
      target: { value: "verified" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Assessment speichern" }));

    expect((await screen.findByRole("alert")).textContent).toMatch(/konkreten Nachweis/i);
    expect(mockUpdate).not.toHaveBeenCalled();
  });

  it("requires both control owner and reviewer before verification", async () => {
    render(<TransparencyAssuranceWorkspace tenantId="tenant-1" initialData={fixture()} />);

    fireEvent.change(screen.getAllByLabelText("Kontrollstatus")[0], {
      target: { value: "verified" },
    });
    fireEvent.change(screen.getAllByLabelText("Evidenzreferenz")[0], {
      target: { value: "evidence://interaction-notice/v1" },
    });
    fireEvent.change(screen.getByLabelText("Rolle in der AI-Wertschöpfungskette"), {
      target: { value: "provider" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Assessment speichern" }));

    expect((await screen.findByRole("alert")).textContent).toMatch(/Control Owner, Reviewer/i);
    expect(mockUpdate).not.toHaveBeenCalled();
  });

  it("persists all six controls with optimistic version and refreshes the summary", async () => {
    mockUpdate.mockResolvedValue(fixture(1).systems[0].assessment);
    mockFetch.mockResolvedValue(fixture(1));
    render(<TransparencyAssuranceWorkspace tenantId="tenant-1" initialData={fixture()} />);

    fireEvent.click(screen.getByRole("button", { name: "Assessment speichern" }));

    await waitFor(() => expect(mockUpdate).toHaveBeenCalledTimes(1));
    expect(mockUpdate).toHaveBeenCalledWith(
      "tenant-1",
      "sys-1",
      expect.objectContaining({
        expected_version: 0,
        controls: expect.arrayContaining([
          expect.objectContaining({ control_key: "gdpr_transparency_notice" }),
        ]),
      }),
    );
    const body = mockUpdate.mock.calls[0][2];
    expect(body.controls).toHaveLength(6);
    await waitFor(() => expect(mockFetch).toHaveBeenCalledWith("tenant-1"));
  });
});
