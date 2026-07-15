import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TrustAssuranceExplorer } from "./TrustAssuranceExplorer";

describe("TrustAssuranceExplorer", () => {
  it("separates the productive public scope from evidence-gated enterprise controls", () => {
    render(<TrustAssuranceExplorer />);

    expect(
      screen.getByRole("heading", { name: "Klar begrenzter öffentlicher Scope." }),
    ).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /Enterprise Boundary/ }));

    expect(
      screen.getByRole("heading", { name: "Enterprise-Funktionen bleiben fail-closed." }),
    ).toBeTruthy();
    expect(screen.getByText("Evidenzpflichtig")).toBeTruthy();
  });
});
