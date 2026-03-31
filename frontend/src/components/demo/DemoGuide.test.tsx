import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DemoGuide } from "./DemoGuide";

vi.mock("next/navigation", () => ({
  usePathname: () => "/tenant/ai-governance-playbook",
  useRouter: () => ({ push: vi.fn() }),
}));

describe("DemoGuide", () => {
  it("rendert nichts wenn disabled", () => {
    const { container } = render(<DemoGuide tenantId="t1" enabled={false} />);
    expect(container.textContent).toBe("");
  });

  it("zeigt Demo-Guide Button wenn enabled", () => {
    render(<DemoGuide tenantId="t1" enabled />);
    expect(screen.getByRole("button", { name: /Demo-Guide/i })).toBeTruthy();
  });
});
