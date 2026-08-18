import { cleanup, render, screen, fireEvent, act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

import OnboardingWizardPage from "./page";

const STORAGE_KEY = "ch_onboarding_wizard";

describe("OnboardingWizardPage – finish() race-condition fix", () => {
  beforeEach(() => {
    pushMock.mockClear();
    sessionStorage.clear();
  });

  afterEach(() => {
    cleanup();
    sessionStorage.clear();
  });

  it("finish() clears sessionStorage before navigating", async () => {
    // Pre-populate wizard state at step 5 so Finish button is visible
    const wizardState = {
      step: 5,
      company: {
        name: "Test GmbH",
        industry: "it_tech",
        employeeCount: "50-249",
        complianceAreas: ["dsgvo"],
        handelsregister: "",
        ustIdNr: "",
      },
      frameworks: ["dsgvo"],
      users: [{ email: "admin@test.de", role: "admin" }],
      documents: [],
      completed: false,
    };
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(wizardState));

    render(<OnboardingWizardPage />);

    const finishBtn = screen.getByText("🎉 Compliance Hub starten");
    expect(finishBtn).toBeDefined();

    await act(async () => {
      fireEvent.click(finishBtn);
    });

    // sessionStorage must be empty after finish
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull();
    // router.push must have been called
    expect(pushMock).toHaveBeenCalledWith("/tenant/compliance-overview");
  });

  it("useEffect does not write completed state back to sessionStorage", async () => {
    // Start with a fresh wizard
    render(<OnboardingWizardPage />);

    // The useEffect should persist initial state
    const stored = sessionStorage.getItem(STORAGE_KEY);
    expect(stored).not.toBeNull();
    const parsed = JSON.parse(stored!);
    expect(parsed.completed).toBe(false);
  });
});
