import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { HomeProductPreview } from "./HomeProductPreview";

describe("HomeProductPreview", () => {
  afterEach(cleanup);

  it("labels the preview as illustrative and avoids invented performance metrics", () => {
    render(<HomeProductPreview />);

    expect(screen.getByText("Illustrative Produktlogik")).toBeTruthy();
    expect(
      screen.getByRole("heading", {
        name: "Pflicht und Verantwortlichkeit im selben Kontext",
      }),
    ).toBeTruthy();
    expect(screen.queryByText(/%/)).toBeNull();
  });

  it("switches between control, evidence and board context with accessible tabs", () => {
    render(<HomeProductPreview />);

    fireEvent.click(screen.getByRole("tab", { name: "Evidence Review" }));

    expect(
      screen.getByRole("heading", {
        name: "Nachweis mit Herkunft und Review-Kontext",
      }),
    ).toBeTruthy();
    expect(
      screen.getByRole("tab", { name: "Evidence Review" }).getAttribute("aria-selected"),
    ).toBe("true");

    fireEvent.click(screen.getByRole("tab", { name: "Board Context" }));
    expect(
      screen.getByText(
        "Automatische Rechts- und Freigabeentscheidungen bleiben ausgeschlossen.",
      ),
    ).toBeTruthy();
  });
});
