import { cleanup, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

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
    cleanup();
    vi.clearAllMocks();
    if (saved === undefined) delete process.env.NEXT_PUBLIC_FEATURE_WHAT_IF_SIMULATOR;
    else process.env.NEXT_PUBLIC_FEATURE_WHAT_IF_SIMULATOR = saved;
  });

  it("shows what-if panel when flag enabled", async () => {
    const { unmount } = render(<BoardWhatIfSimulatorClient />);
    await waitFor(() => {
      expect(screen.getByTestId("board-what-if-panel")).toBeTruthy();
    });
    expect(screen.getByRole("heading", { name: /What-if-Simulator/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Simulation berechnen/i })).toBeTruthy();
    unmount();
    await waitFor(() => {
      expect(screen.queryByTestId("board-what-if-panel")).toBeNull();
    });
  });

  it("hides when what-if flag is off", () => {
    process.env.NEXT_PUBLIC_FEATURE_WHAT_IF_SIMULATOR = "0";
    const { container, unmount } = render(<BoardWhatIfSimulatorClient />);
    expect(container.firstChild).toBeNull();
    unmount();
  });
});
