import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { Exhibit } from "./Primitives";

/**
 * Die Exhibit-Ebene ist der Teil dieser Website, der eine Abbildung von einer
 * Illustration unterscheidet. Sie steht und fällt mit drei Eigenschaften:
 * einer zitierbaren Nummer, einer Kernaussage als Titel und einer Quellenzeile.
 * Fehlt eine davon, ist die Abbildung wieder Dekoration.
 */
describe("Exhibit", () => {
  afterEach(cleanup);

  it("nummeriert die Abbildung zitierbar", () => {
    render(
      <Exhibit index={3} claim="Ein Control trägt sechs Nachweispflichten.">
        <div data-testid="figure" />
      </Exhibit>,
    );
    // Das Label steht als zwei Textknoten im selben `span` und trägt ein
    // geschütztes Leerzeichen — „Exhibit 3" darf nie umbrechen. Der
    // Funktions-Matcher prüft deshalb den zusammengesetzten Elementinhalt.
    const label = screen.getByText(
      (_content, element) =>
        element?.className === "mk-exhibit__index" &&
        element.textContent?.replace(/\s+/g, " ") === "Exhibit 3",
    );
    expect(label).toBeTruthy();
    expect(screen.getByTestId("figure")).toBeTruthy();
  });

  it("führt immer eine Quellenzeile, auch ohne explizite Angabe", () => {
    render(
      <Exhibit index={1} claim="Aussage">
        <div />
      </Exhibit>,
    );
    expect(screen.getByText("Quelle")).toBeTruthy();
    // Der Standard weist die Ansicht als Beispieldaten aus. Eine Produktansicht
    // ohne diesen Hinweis könnte als Kundendatenausschnitt gelesen werden.
    expect(screen.getByText(/Beispieldaten/)).toBeTruthy();
  });

  it("zeigt Lesart und Grundlage nur, wenn sie angegeben sind", () => {
    const { rerender } = render(
      <Exhibit index={1} claim="Aussage">
        <div />
      </Exhibit>,
    );
    expect(screen.queryByText("Lesart")).toBeNull();
    expect(screen.queryByText("Grundlage")).toBeNull();

    rerender(
      <Exhibit
        index={1}
        claim="Aussage"
        reading="Links das Control, rechts die Regelwerke."
        basis="EU AI Act Art. 9"
      >
        <div />
      </Exhibit>,
    );
    expect(screen.getByText("Lesart")).toBeTruthy();
    expect(screen.getByText("Grundlage")).toBeTruthy();
    expect(screen.getByText("EU AI Act Art. 9")).toBeTruthy();
  });

  it("rahmt die Abbildung als helle Unterlage, wenn sie auf der Bühne liegt", () => {
    const { container } = render(
      <Exhibit index={1} claim="Aussage" paper>
        <div data-testid="figure" />
      </Exhibit>,
    );
    // `mk-mat` ist das Passepartout, `mk-paper` schaltet die Rollen darin auf
    // hell zurück — sonst stünde ein auf Weiß kalibriertes Diagramm auf Navy.
    expect(container.querySelector(".mk-mat")).toBeTruthy();
    expect(container.querySelector(".mk-paper")).toBeTruthy();
  });

  it("nutzt figure/figcaption, damit die Bildunterschrift zugeordnet ist", () => {
    const { container } = render(
      <Exhibit index={1} claim="Aussage">
        <div />
      </Exhibit>,
    );
    const figure = container.querySelector("figure");
    expect(figure).toBeTruthy();
    expect(figure?.querySelector("figcaption")).toBeTruthy();
  });
});

/**
 * Die Nummerierung ist nur zitierbar, wenn sie stimmt. Ein Sprung von
 * „Exhibit 3" auf „Exhibit 5" fällt beim Lesen nicht auf, in einer Sitzung
 * mit dem Ausdruck auf dem Tisch aber sofort.
 */
describe("Exhibit-Nummerierung der öffentlichen Seiten", () => {
  const pages = ["../../../app/(marketing)/page.tsx", "../../../app/(marketing)/plattform/page.tsx"];

  for (const page of pages) {
    it(`ist lückenlos und beginnt bei 1: ${page.split("(marketing)")[1]}`, () => {
      const source = readFileSync(resolve(__dirname, page), "utf8");
      const indices = [...source.matchAll(/index=\{(\d+)\}/g)].map((m) => Number(m[1]));
      expect(indices.length).toBeGreaterThan(0);
      expect(indices).toEqual(indices.map((_, i) => i + 1));
    });
  }
});
