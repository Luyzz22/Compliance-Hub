import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { BoardWhatIfSimulatorClient } from "./BoardWhatIfSimulatorClient";

const mockSystems = vi.fn();

vi.mock("@/lib/api", () => ({
  fetchTenantAISystems: (...a: unknown[]) => mockSystems(...a),
  postWhatIfBoardImpact: vi.fn(),
}));

describe("BoardWhatIfSimulatorClient", () => {
  const saved = process.env.NEXT_PUBLIC_FEATURE_WHAT_IF_SIMULATOR;

  beforeEach(() => {
    process.env.NEXT_PUBLIC_FEATURE_WHAT_IF_SIMULATOR = "1";
    mockSystems.mockResolvedValue([
      {
        id: "hr-1",
        name: "High Risk One",
        risk_level: "high",
      },
    ]);
  });

  afterEach(() => {
    vi.clearAllMocks();
    if (saved === undefined) delete process.env.NEXT_PUBLIC_FEATURE_WHAT_IF_SIMULATOR;
    else process.env.NEXT_PUBLIC_FEATURE_WHAT_IF_SIMULATOR = saved;
  });

  it("shows what-if panel when flag enabled", async () => {
    render(<BoardWhatIfSimulatorClient />);
    await waitFor(() => {
      expect(screen.getByTestId("board-what-if-panel")).toBeTruthy();
    });
    expect(screen.getByRole("heading", { name: /What-if-Simulator/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Simulation berechnen/i })).toBeTruthy();
  });

  it("hides when what-if flag is off", () => {
    process.env.NEXT_PUBLIC_FEATURE_WHAT_IF_SIMULATOR = "0";
    const { container } = render(<BoardWhatIfSimulatorClient />);
    expect(container.firstChild).toBeNull();
  });
});
