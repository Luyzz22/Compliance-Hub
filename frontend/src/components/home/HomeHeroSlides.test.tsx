import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HomeHeroSlides } from "./HomeHeroSlides";

describe("HomeHeroSlides", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "matchMedia",
      vi.fn().mockReturnValue({
        matches: true,
        media: "(prefers-reduced-motion: reduce)",
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }),
    );
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("exposes three controllable and accurately labelled perspectives", () => {
    render(<HomeHeroSlides />);

    expect(
      screen.getByRole("heading", {
        name: "Vom AI-Inventar zum kontrollierten System.",
      }),
    ).toBeTruthy();
    expect(screen.getAllByRole("tab")).toHaveLength(3);
    expect(screen.getAllByRole("img", { hidden: true })).toHaveLength(3);

    fireEvent.click(screen.getByRole("tab", { name: /Evidence Chain/ }));

    expect(
      screen.getByRole("heading", {
        name: "Evidence, die Herkunft und Review sichtbar macht.",
      }),
    ).toBeTruthy();
    expect(
      screen
        .getByRole("tab", { name: /Evidence Chain/ })
        .getAttribute("aria-selected"),
    ).toBe("true");
  });

  it("supports sequential navigation and a visible motion control", () => {
    render(<HomeHeroSlides />);

    fireEvent.click(screen.getByRole("button", { name: "Nächste Slide" }));
    expect(
      screen
        .getByRole("tab", { name: /Evidence Chain/ })
        .getAttribute("aria-selected"),
    ).toBe("true");

    fireEvent.click(
      screen.getByRole("button", { name: "Automatischen Wechsel pausieren" }),
    );
    expect(
      screen.getByRole("button", { name: "Automatischen Wechsel starten" })
        .textContent,
    ).toContain("Abspielen");
  });
});
