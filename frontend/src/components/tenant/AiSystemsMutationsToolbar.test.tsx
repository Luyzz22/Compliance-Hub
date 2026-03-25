import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AiSystemsMutationsToolbar } from "./AiSystemsMutationsToolbar";

const mockUse = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

vi.mock("@/hooks/useWorkspaceMode", () => ({
  useWorkspaceMode: () => mockUse(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    importAiSystemsFile: vi.fn(),
  };
});

afterEach(() => {
  cleanup();
});

describe("AiSystemsMutationsToolbar", () => {
  it("deaktiviert CTAs wenn mutationsBlocked", () => {
    mockUse.mockReturnValue({
      mutationsBlocked: true,
      modeHint: "Demo read-only",
    });
    render(<AiSystemsMutationsToolbar tenantId="t-demo" />);
    expect((screen.getByTestId("ai-systems-new-placeholder") as HTMLButtonElement).disabled).toBe(
      true,
    );
    expect((screen.getByTestId("ai-systems-import-trigger") as HTMLButtonElement).disabled).toBe(
      true,
    );
  });

  it("aktiviert CTAs in Produktiv-Modus", () => {
    mockUse.mockReturnValue({
      mutationsBlocked: false,
      modeHint: "",
    });
    render(<AiSystemsMutationsToolbar tenantId="t-prod" />);
    expect((screen.getByTestId("ai-systems-new-placeholder") as HTMLButtonElement).disabled).toBe(
      false,
    );
    expect((screen.getByTestId("ai-systems-import-trigger") as HTMLButtonElement).disabled).toBe(
      false,
    );
  });
});
