import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { FrameworkMappingGraph } from "./FrameworkMappingGraph";

describe("FrameworkMappingGraph", () => {
  afterEach(cleanup);

  it("zeigt das gewählte Control mit Owner, Evidenz und Review-Zyklus", () => {
    render(<FrameworkMappingGraph />);

    expect(screen.getByText("Control: KI-Risikobeurteilung")).toBeTruthy();
    expect(screen.getByText("J. Petrova · AI Risk Officer")).toBeTruthy();
    expect(screen.getByText("Quartalsweise")).toBeTruthy();
  });

  it("führt jedes Regelwerk mit einer konkreten Fundstelle statt pauschaler Zuordnung", () => {
    render(<FrameworkMappingGraph />);

    expect(screen.getByText("Art. 9")).toBeTruthy();
    expect(screen.getByText("Art. 21 Abs. 2 a")).toBeTruthy();
    expect(screen.getByText("Art. 35")).toBeTruthy();
    expect(screen.getAllByText("gemappt")).toHaveLength(6);
  });

  it("wechselt beim Umschalten des Controls auf dessen Zuordnungen", () => {
    render(<FrameworkMappingGraph />);

    fireEvent.click(
      screen.getByRole("tab", { name: /Protokollierung & Aufzeichnungen/ }),
    );

    expect(screen.getByText("Control: Protokollierung & Aufzeichnungen")).toBeTruthy();
    expect(screen.getByText("Art. 12 · Art. 19")).toBeTruthy();
    expect(screen.getByText("A.8.15")).toBeTruthy();
    expect(screen.queryByText("Control: KI-Risikobeurteilung")).toBeNull();
  });

  it("hebt ein Regelwerk auf Klick hervor und gibt die Hervorhebung wieder frei", () => {
    render(<FrameworkMappingGraph />);

    const list = screen.getByRole("list");
    const nis2 = within(list).getByRole("button", { name: /NIS2/ });

    fireEvent.click(nis2);
    expect(nis2.getAttribute("aria-pressed")).toBe("true");

    fireEvent.click(nis2);
    expect(nis2.getAttribute("aria-pressed")).toBe("false");
  });
});
