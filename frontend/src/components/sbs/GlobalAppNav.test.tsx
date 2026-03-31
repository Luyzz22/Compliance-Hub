import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

vi.mock("./GlobalWorkspaceEvidenceNavBlock", () => ({
  GlobalWorkspaceEvidenceNavBlock: () => null,
}));

const isAdvisorNavEnabled = vi.fn();

vi.mock("@/lib/api", () => ({
  isAdvisorNavEnabled: () => isAdvisorNavEnabled(),
}));

import { GlobalAppNav } from "./GlobalAppNav";

describe("GlobalAppNav", () => {
  afterEach(() => {
    cleanup();
    isAdvisorNavEnabled.mockReset();
  });

  it("shows Advisor link when isAdvisorNavEnabled is true", () => {
    isAdvisorNavEnabled.mockReturnValue(true);
    render(<GlobalAppNav />);
    expect(screen.getByRole("link", { name: /^Advisor$/i })).toBeTruthy();
  });

  it("hides Advisor link when isAdvisorNavEnabled is false", () => {
    isAdvisorNavEnabled.mockReturnValue(false);
    render(<GlobalAppNav />);
    expect(screen.queryByRole("link", { name: /^Advisor$/i })).toBeNull();
  });
});
