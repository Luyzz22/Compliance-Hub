import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DemoEnvironmentBanner } from "./DemoEnvironmentBanner";

describe("DemoEnvironmentBanner", () => {
  it("rendert nichts wenn visible false", () => {
    const { container } = render(<DemoEnvironmentBanner visible={false} />);
    expect(container.firstChild).toBeNull();
  });

  it("zeigt Demo-Hinweis wenn visible true", () => {
    render(<DemoEnvironmentBanner visible />);
    const el = screen.getByRole("status");
    expect(el.textContent).toContain("Demo-Umgebung");
    expect(el.textContent).toContain("zurückgesetzt");
  });
});
