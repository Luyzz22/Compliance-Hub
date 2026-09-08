import { describe, expect, it } from "vitest";

import { HOUSE, SISTER_PRODUCTS } from "./houseIdentity";

/**
 * Das Herkunftsband erscheint auf jeder öffentlichen Seite und macht damit
 * Aussagen über ein reales Unternehmen. Diese Tests halten fest, welche
 * Aussagen dort *nicht* stehen dürfen — der teuerste Fehler auf einer Seite,
 * deren ganzes Argument Nachweisbarkeit ist, wäre eine Herkunftsangabe, die
 * dem eigenen Impressum widerspricht.
 */
describe("houseIdentity", () => {
  it("nennt die Dachmarke ohne Rechtsformzusatz", () => {
    // Die Firmierung kommt aus `getLegalConfig()` und damit aus der geprüften
    // Umgebungskonfiguration. Stünde sie hier zusätzlich als Literal, gäbe es
    // zwei Quellen für dieselbe Pflichtangabe — und irgendwann zwei Fassungen.
    expect(HOUSE.name).toBe("SBS Deutschland");
    expect(HOUSE.name).not.toMatch(/GmbH|KG|AG|UG|mbH|e\.K\./i);
    expect(HOUSE.imprintHref).toBe("/impressum");
  });

  it("führt keine Anschrift, Registerangaben oder Zertifizierungsaussagen", () => {
    const text = JSON.stringify({ HOUSE, SISTER_PRODUCTS });
    const forbidden = [
      /\bHRA?\s?\d/i, // Registernummer
      /\bUSt-IdNr|DE\d{9}\b/i, // Umsatzsteuer-ID
      /\bstraße\b|\bstrasse\b|\bStr\.\s?\d/i, // Anschrift
      /\b\d{5}\s+[A-ZÄÖÜ]/, // Postleitzahl mit Ort
      /zertifiziert|zertifizierung|ISO\s?27001\s?zertifi/i,
      /garantiert|100\s?%\s?konform/i,
      /Serverstandort|Rechenzentrum|Datenresidenz/i,
    ];
    for (const pattern of forbidden) {
      expect(text).not.toMatch(pattern);
    }
  });

  it("verweist auf das Schwesterprodukt mit abgrenzender Beschreibung", () => {
    const normpilot = SISTER_PRODUCTS.find((p) => p.name === "NormPilot Industrie");
    expect(normpilot).toBeDefined();
    expect(normpilot?.href).toBe("https://www.normpilot-industrie.de");
    // Die Beschreibung soll abgrenzen, nicht bewerben: sie nennt den
    // Anwendungsbereich und kommt ohne Superlative aus.
    expect(normpilot?.scope).toMatch(/Fertigung|Produktdokumentation/);
    expect(normpilot?.scope).not.toMatch(
      /führend|beste|einzigartig|revolutionär|marktführ/i,
    );
  });

  it("verlinkt die Unternehmenswebsite über HTTPS", () => {
    expect(HOUSE.corporateUrl).toMatch(/^https:\/\//);
    for (const product of SISTER_PRODUCTS) {
      expect(product.href).toMatch(/^https:\/\//);
    }
  });
});
