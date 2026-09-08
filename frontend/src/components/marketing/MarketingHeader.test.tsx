import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MarketingHeader } from "./MarketingHeader";

vi.mock("next/navigation", () => ({
  usePathname: () => "/plattform",
}));

describe("MarketingHeader", () => {
  afterEach(cleanup);

  it("führt die Hauptbereiche der Informationsarchitektur", () => {
    render(<MarketingHeader />);

    const nav = screen.getByRole("navigation", { name: "Hauptnavigation" });
    for (const label of [
      "Plattform",
      "Lösungen",
      "Für Beratungen",
      "Integrationen",
      "Sicherheit",
      "Ressourcen",
      "Unternehmen",
    ]) {
      expect(nav.textContent).toContain(label);
    }
    expect(screen.getAllByRole("link", { name: "Demo anfragen" }).length).toBeGreaterThan(0);
  });

  it("öffnet ein Menü und schließt es mit Escape", () => {
    render(<MarketingHeader />);

    const trigger = screen.getByRole("button", { name: /Lösungen/ });
    expect(trigger.getAttribute("aria-expanded")).toBe("false");

    fireEvent.click(trigger);
    expect(trigger.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByRole("menuitem", { name: /EU AI Act & ISO 42001/ })).toBeTruthy();

    fireEvent.keyDown(document, { key: "Escape" });
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
  });

  it("bietet den Login nur an, wenn eine Anmeldung im Release existiert", () => {
    const { rerender } = render(<MarketingHeader showLogin={false} />);
    expect(screen.queryByRole("link", { name: "Login" })).toBeNull();

    rerender(<MarketingHeader showLogin />);
    expect(screen.getByRole("link", { name: "Login" }).getAttribute("href")).toBe(
      "/auth/login",
    );
  });

  it("öffnet und schließt die mobile Navigation", () => {
    render(<MarketingHeader />);

    const toggle = screen.getByRole("button", { name: "Menü öffnen" });
    fireEvent.click(toggle);

    expect(screen.getByRole("navigation", { name: "Hauptnavigation mobil" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Menü schließen" }));
    expect(screen.queryByRole("navigation", { name: "Hauptnavigation mobil" })).toBeNull();
  });
});

/**
 * Die Kopfzeile trug die Desktop-Navigation ab `lg` (1024px). Dort passen
 * Marke, sieben Navigationsgruppen, Login und zwei Aktionen nicht nebeneinander
 * — die Leiste lief um 100px über den Viewport hinaus, auf jeder Seite.
 *
 * Sichtbar war das nicht als Überlauf, sondern als „Comp…": die Wortmarke trug
 * `truncate` und schluckte die fehlende Breite. Diese Tests halten beides fest
 * — den Umschaltpunkt und das Fehlen der Notlösung.
 */
describe("MarketingHeader — responsiver Vertrag", () => {
  afterEach(cleanup);

  it("schaltet Navigation und Menütaste am selben Punkt um", () => {
    const { container } = render(<MarketingHeader />);

    const nav = container.querySelector('nav[aria-label="Hauptnavigation"]');
    const toggle = screen.getByRole("button", { name: "Menü öffnen" });

    // Genau ein Umschaltpunkt: sonst gäbe es eine Breite, in der beide
    // sichtbar sind — oder schlimmer, keine von beiden.
    expect(nav?.className).toContain("xl:flex");
    expect(nav?.className).toContain("hidden");
    expect(toggle.className).toContain("xl:hidden");
  });

  it("kürzt die Wortmarke nicht", () => {
    const { container } = render(<MarketingHeader />);
    const wordmark = screen.getByText("Compliance Hub");

    expect(wordmark.className).not.toContain("truncate");
    expect(wordmark.className).toContain("whitespace-nowrap");

    // Auch der Markenlink darf nicht schrumpfen — täte er es, wäre der
    // Überlauf wieder unsichtbar statt behoben.
    const brandLink = container.querySelector('a[href="/"]');
    expect(brandLink?.className).toContain("shrink-0");
  });
});
