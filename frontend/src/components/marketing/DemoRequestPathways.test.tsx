import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { DemoRequestPathways } from "./DemoRequestPathways";

describe("DemoRequestPathways", () => {
  afterEach(cleanup);

  it("weist auf den zustandslosen öffentlichen Release hin", () => {
    render(<DemoRequestPathways />);

    expect(screen.getByText(/verarbeitet keine Formulardaten/)).toBeTruthy();
  });

  it("bereitet je Format eine eigene Nachricht mit passendem Betreff vor", () => {
    render(<DemoRequestPathways />);

    const link = () => screen.getByRole("link", { name: "Nachricht vorbereiten" });
    expect(link().getAttribute("href")).toContain(
      encodeURIComponent("Compliance Hub – Governance-Demo"),
    );

    fireEvent.click(screen.getByRole("button", { name: /Partner-Demo/ }));

    expect(screen.getByText("Mandantenbetrieb und Portfoliosicht")).toBeTruthy();
    expect(link().getAttribute("href")).toContain(
      encodeURIComponent("Compliance Hub – Partner-Demo"),
    );
  });

  it("markiert das aktive Format für Tastatur- und Screenreader-Nutzung", () => {
    render(<DemoRequestPathways />);

    const security = screen.getByRole("button", { name: /Security & Architektur/ });
    expect(security.getAttribute("aria-pressed")).toBe("false");

    fireEvent.click(security);
    expect(security.getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByText("Isolation, Zugriffe, Protokollierung")).toBeTruthy();
  });
});
