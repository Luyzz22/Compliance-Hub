import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ProductTourSimulation } from "./ProductTourSimulation";

describe("ProductTourSimulation", () => {
  afterEach(cleanup);

  it("startet beim Geltungsbereich und kennzeichnet die Ansicht als illustrativ", () => {
    render(<ProductTourSimulation />);

    expect(
      screen.getByRole("heading", { name: "Sie legen fest, worüber gesprochen wird." }),
    ).toBeTruthy();
    expect(screen.getByRole("tab", { name: /Geltungsbereich/ }).getAttribute("aria-selected")).toBe(
      "true",
    );
    expect(screen.getByText(/Illustrative Produktansicht/)).toBeTruthy();
  });

  it("führt über die Schaltflächen sequenziell durch alle fünf Schritte", () => {
    render(<ProductTourSimulation />);

    const next = screen.getByRole("button", { name: "Weiter" });
    const back = screen.getByRole("button", { name: "Zurück" });

    expect(back.hasAttribute("disabled")).toBe(true);

    fireEvent.click(next);
    expect(screen.getByRole("heading", { name: /Die Systeme kommen ins Register/ })).toBeTruthy();

    fireEvent.click(next);
    fireEvent.click(next);
    fireEvent.click(next);
    expect(
      screen.getByRole("heading", { name: "Der Bericht entsteht aus dem laufenden Stand." }),
    ).toBeTruthy();
    expect(next.hasAttribute("disabled")).toBe(true);

    fireEvent.click(back);
    expect(
      screen.getByRole("heading", { name: "Ein Control trägt mehrere Nachweispflichten." }),
    ).toBeTruthy();
  });

  it("springt über die Schrittliste direkt zur Risikoklassifizierung", () => {
    render(<ProductTourSimulation />);

    fireEvent.click(screen.getByRole("tab", { name: /Klassifizierung/ }));

    expect(screen.getByText("Hochrisiko · Anhang III Nr. 4 (Beschäftigung)")).toBeTruthy();
    expect(screen.getByText("Maßnahme M-118 · fällig 30.09.2026")).toBeTruthy();
  });
});
