import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TenantNav } from "./TenantNav";

const mockPathname = vi.fn(() => "/tenant/impact-assessments");

vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname(),
}));

vi.mock("@/hooks/useAiActEvidenceNav", () => ({
  useAiActEvidenceNav: () => ({
    visible: true,
    href: "/tenants/tenant-1/evidence/ai-act",
    loading: false,
  }),
}));

afterEach(() => {
  cleanup();
  mockPathname.mockReturnValue("/tenant/impact-assessments");
});

describe("TenantNav", () => {
  it("groups enterprise work by user intent and exposes existing control surfaces", () => {
    render(<TenantNav workspaceTenantId="tenant-1" />);

    expect(screen.getByRole("heading", { name: "Steuerung" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Assessments" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Betrieb & Evidenz" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Enterprise Control Center" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "DSFA & FRIA" }).getAttribute("aria-current")).toBe("page");
    expect(screen.getByRole("link", { name: "Onboarding Readiness" })).toBeTruthy();
  });

  it("filters labels and compliance keywords without removing the active destination", () => {
    render(<TenantNav workspaceTenantId="tenant-1" />);

    fireEvent.change(screen.getByLabelText("Workspace-Navigation filtern"), {
      target: { value: "Datenschutz Folgenabschätzung" },
    });

    expect(screen.getByRole("link", { name: "DSFA & FRIA" })).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Enterprise Control Center" })).toBeNull();
  });

  it("announces an empty navigation result", () => {
    render(<TenantNav workspaceTenantId="tenant-1" />);

    fireEvent.change(screen.getByLabelText("Workspace-Navigation filtern"), {
      target: { value: "nicht-vorhanden-123" },
    });

    expect(screen.getByRole("status").textContent).toMatch(/Keine Navigation/i);
  });
});
