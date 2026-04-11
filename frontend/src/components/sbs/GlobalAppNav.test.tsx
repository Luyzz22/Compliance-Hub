import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("./GlobalWorkspaceEvidenceNavBlock", () => ({
  GlobalWorkspaceEvidenceNavBlock: () => null,
}));

vi.mock("./UpgradeModal", () => ({
  UpgradeModal: () => null,
}));

const isAdvisorNavEnabled = vi.fn();

vi.mock("@/lib/api", () => ({
  isAdvisorNavEnabled: () => isAdvisorNavEnabled(),
}));

const mockUseCanSeeAdmin = vi.fn();
const mockUseCanSeeReporting = vi.fn();
const mockUseCanSeeAiSystems = vi.fn();

vi.mock("@/hooks/useUserRole", () => ({
  useCanSeeAdmin: () => mockUseCanSeeAdmin(),
  useCanSeeReporting: () => mockUseCanSeeReporting(),
  useCanSeeAiSystems: () => mockUseCanSeeAiSystems(),
}));

vi.mock("@/hooks/useFeatureGate", () => ({
  useFeatureGate: () => ({
    isGated: () => false,
    requiredPlanLabel: () => "Professional",
  }),
}));

import { GlobalAppNav } from "./GlobalAppNav";

describe("GlobalAppNav", () => {
  afterEach(() => {
    cleanup();
    isAdvisorNavEnabled.mockReset();
    mockUseCanSeeAdmin.mockReset();
    mockUseCanSeeReporting.mockReset();
    mockUseCanSeeAiSystems.mockReset();
  });

  function setupDefaults() {
    isAdvisorNavEnabled.mockReturnValue(false);
    mockUseCanSeeAdmin.mockReturnValue(true);
    mockUseCanSeeReporting.mockReturnValue(true);
    mockUseCanSeeAiSystems.mockReturnValue(true);
  }

  it("shows Advisor link when isAdvisorNavEnabled is true", () => {
    setupDefaults();
    isAdvisorNavEnabled.mockReturnValue(true);
    render(<GlobalAppNav />);
    expect(screen.getByRole("link", { name: /^Advisor$/i })).toBeTruthy();
  });

  it("hides Advisor link when isAdvisorNavEnabled is false", () => {
    setupDefaults();
    render(<GlobalAppNav />);
    expect(screen.queryByRole("link", { name: /^Advisor$/i })).toBeNull();
  });

  it("renders Reporting dropdown button when role has access", () => {
    setupDefaults();
    render(<GlobalAppNav />);
    expect(screen.getByRole("button", { name: /Reporting/i })).toBeTruthy();
  });

  it("renders Admin dropdown button when role has access", () => {
    setupDefaults();
    render(<GlobalAppNav />);
    expect(screen.getByRole("button", { name: /Admin/i })).toBeTruthy();
  });

  it("renders AI Systems link when role has access", () => {
    setupDefaults();
    render(<GlobalAppNav />);
    expect(screen.getByRole("link", { name: /AI Systems/i })).toBeTruthy();
  });

  it("renders user account menu button", () => {
    setupDefaults();
    render(<GlobalAppNav />);
    expect(screen.getByRole("button", { name: /Konto/i })).toBeTruthy();
  });

  // ── RBAC tests ─────────────────────────────────────────────

  it("VIEWER sees no Admin dropdown", () => {
    setupDefaults();
    mockUseCanSeeAdmin.mockReturnValue(false);
    render(<GlobalAppNav />);
    expect(screen.queryByRole("button", { name: /Admin/i })).toBeNull();
  });

  it("VIEWER sees no Reporting dropdown", () => {
    setupDefaults();
    mockUseCanSeeReporting.mockReturnValue(false);
    render(<GlobalAppNav />);
    expect(screen.queryByRole("button", { name: /Reporting/i })).toBeNull();
  });

  it("VIEWER sees no AI Systems link", () => {
    setupDefaults();
    mockUseCanSeeAiSystems.mockReturnValue(false);
    render(<GlobalAppNav />);
    expect(screen.queryByRole("link", { name: /AI Systems/i })).toBeNull();
  });

  it("TENANT_ADMIN sees Admin dropdown", () => {
    setupDefaults();
    mockUseCanSeeAdmin.mockReturnValue(true);
    render(<GlobalAppNav />);
    expect(screen.getByRole("button", { name: /Admin/i })).toBeTruthy();
  });

  it("BOARD_MEMBER sees Reporting but no Admin", () => {
    setupDefaults();
    mockUseCanSeeAdmin.mockReturnValue(false);
    mockUseCanSeeReporting.mockReturnValue(true);
    render(<GlobalAppNav />);
    expect(screen.getByRole("button", { name: /Reporting/i })).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Admin/i })).toBeNull();
  });

  it("renders mobile hamburger button", () => {
    setupDefaults();
    render(<GlobalAppNav />);
    expect(screen.getByRole("button", { name: /Menü öffnen/i })).toBeTruthy();
  });
});
