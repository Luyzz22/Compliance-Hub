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
