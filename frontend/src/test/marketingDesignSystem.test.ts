import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

/**
 * Vertrag der öffentlichen Designebene „Blue-Brass Evidence".
 *
 * Die Tests hier prüfen nicht, ob eine Seite hübsch ist — das entscheidet
 * niemand in einer Assertion. Sie halten die drei Zusagen fest, die sich
 * still verlieren, wenn niemand hinsieht:
 *
 *   1. Die Hausfarbe ist dieselbe wie beim Schwesterprodukt NormPilot.
 *      Verschiebt sie sich um ein paar Prozent, sehen zwei Produkte
 *      desselben Anbieters aus wie zwei Anbieter.
 *   2. Text erreicht auf beiden Belegungen — heller Unterlage und dunkler
 *      Bühne — die Kontrastschwellen der WCAG 2.1. Die dunkle Bühne ist
 *      genau die Stelle, an der Kontrast unbemerkt verloren geht.
 *   3. Bewegung bleibt abschaltbar.
 */

function readCss(relativePath: string): string {
  return readFileSync(resolve(__dirname, relativePath), "utf8");
}

/**
 * Kommentare entfernen.
 *
 * Die Dateien nennen die abgelegten Farben ausdrücklich — „vorher stand hier
 * #1668e8" ist die Begründung der Ablösung und gehört in den Quelltext. Der
 * Test darf sie deshalb nicht als Fund werten; er sucht nach Deklarationen,
 * nicht nach Erwähnungen.
 */
function withoutComments(css: string): string {
  return css.replace(/\/\*[\s\S]*?\*\//g, "");
}

const CSS = readCss("../../public/static/css/marketing.css");
const TOKENS = readCss("../../public/static/css/design-tokens.css");
const CSS_RULES = withoutComments(CSS);
const TOKEN_RULES = withoutComments(TOKENS);

/* ── Kontrastrechnung nach WCAG 2.1 ───────────────────────────────── */

function channel(value: number): number {
  const c = value / 255;
  return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

function luminance(hex: string): number {
  const clean = hex.replace("#", "");
  const full =
    clean.length === 3
      ? clean
          .split("")
          .map((c) => c + c)
          .join("")
      : clean;
  const r = channel(parseInt(full.slice(0, 2), 16));
  const g = channel(parseInt(full.slice(2, 4), 16));
  const b = channel(parseInt(full.slice(4, 6), 16));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [light, dark] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (light + 0.05) / (dark + 0.05);
}

/** Farbwerte des Systems — Änderungen hier sind bewusste Markenentscheidungen. */
const BRAND = "#003856"; // Petrol-Navy, Anker der Hausfarbe
const STAGE = "#00182a"; // Bühne
const STAGE_PANEL = "#00243c"; // Panel auf der Bühne
const BRASS = "#b98f42"; // Messing, Fläche der Primäraktion auf der Bühne
const BRASS_INK = "#0c1216"; // Schrift auf der Messingfläche
const PAPER = "#ffffff";

describe("Blue-Brass Designebene — Farbvertrag", () => {
  it("teilt den Marken-Anker mit NormPilot Industrie", () => {
    // #003856 ist in beiden Produkten `brand-700`. Der Wert ist die
    // Verwandtschaft; er darf nicht „ungefähr" stimmen.
    expect(CSS).toContain("--mk-navy-700: #003856;");
    expect(CSS).toContain("--mk-brass-400: #b98f42;");
    expect(TOKENS).toContain("--sbs-navy-brand: #003856;");
  });

  it("führt keine der abgelegten Fremdfarben mehr", () => {
    // Indigo (#3f63ea) war der frühere Primärakzent, #1668e8 und #0969da die
    // Signalblaus der Vorgängerfassungen, Cyan die Farbe der alten
    // Trust-Flächen. Keine davon gehört zu einem Produkt des Hauses.
    for (const legacy of ["#3f63ea", "#2f4fd8", "#1668e8", "#0969da", "#06b6d4"]) {
      expect(CSS_RULES.toLowerCase()).not.toContain(legacy);
      expect(TOKEN_RULES.toLowerCase()).not.toContain(legacy);
    }
  });

  it("setzt Messing als Fläche nur für die Primäraktion auf der Bühne", () => {
    // Die Regel des Hauses: Messing ist Linie, Marke und Icon — nie Fläche.
    // Genau eine Ausnahme trägt das System, und sie steht als `--mk-cta`
    // in der Bühnenbelegung.
    const stageBlock = CSS.slice(
      CSS.indexOf(".mk-stage,\n.mk-dark {"),
      CSS.indexOf(".mk-paper {"),
    );
    expect(stageBlock).toContain("--mk-cta: var(--mk-brass-400);");
    expect(stageBlock).toContain("--mk-cta-ink: var(--mk-slate-950);");
  });
});

describe("Blue-Brass Designebene — Kontrast (WCAG 2.1)", () => {
  it("trägt die Primäraktion auf der Bühne mit AA auch für Kleintext", () => {
    // Messing auf Graphit-Schrift: 6.3:1. Weiß auf Navy wäre kontrastreicher,
    // stand aber neben ebenfalls hellen Panelflächen und war als *die*
    // Handlung der Seite nicht mehr erkennbar.
    expect(contrast(BRASS, BRASS_INK)).toBeGreaterThanOrEqual(4.5);
  });

  it("hält Fließtext auf der Bühne über AA", () => {
    const roles = {
      "fg (weiß)": "#ffffff",
      "fg-soft": "#dde5e9",
      "fg-muted": "#c3cfd6",
      "fg-faint": "#9fb3bf",
    };
    for (const [name, value] of Object.entries(roles)) {
      expect(
        contrast(value, STAGE),
        `${name} auf der Bühne`,
      ).toBeGreaterThanOrEqual(4.5);
      expect(
        contrast(value, STAGE_PANEL),
        `${name} auf dem Bühnenpanel`,
      ).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("hält Fließtext auf heller Unterlage über AA", () => {
    const roles = {
      "fg": "#161e23",
      "fg-soft": "#38444c",
      "fg-muted": "#4e5c65",
      "fg-faint": "#61717c",
      "accent-700 (Marke)": BRAND,
      "accent-600": "#0e4d6e",
      "brass-600 (einzige Messing-Textstufe)": "#8a6626",
    };
    for (const [name, value] of Object.entries(roles)) {
      expect(contrast(value, PAPER), `${name} auf Weiß`).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("hält die Statusfarben auf ihrer jeweiligen Belegung über AA", () => {
    // Status trägt hier Bedeutung, nicht Dekoration — deshalb zwei Sätze:
    // die dunklen Werte für helle Unterlagen, die aufgehellten für die Bühne.
    const onPaper = { ok: "#0f6e4e", warn: "#8a5a0b", crit: "#a32217" };
    for (const [name, value] of Object.entries(onPaper)) {
      expect(contrast(value, PAPER), `${name} auf Weiß`).toBeGreaterThanOrEqual(4.5);
    }

    const onStage = { ok: "#6cc9a2", warn: "#e5b45f", crit: "#f0a49a" };
    for (const [name, value] of Object.entries(onStage)) {
      expect(
        contrast(value, STAGE_PANEL),
        `${name} auf dem Bühnenpanel`,
      ).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("hebt den Fokusring auf der Bühne auf eine sichtbare Stufe", () => {
    // brand-600 verschwindet auf Navy; der Ring wechselt dort auf navy-200.
    expect(CSS).toContain("--mk-focus: var(--mk-navy-200);");
    expect(contrast("#b7d0de", STAGE)).toBeGreaterThanOrEqual(3);
  });
});

describe("Blue-Brass Designebene — Formsprache", () => {
  it("trägt die Messingmarke am Eyebrow als Pseudoelement", () => {
    // Der Strich gehört zur Marke. Läge er im Markup, fehlte er irgendwann
    // an einer Einbindung.
    const eyebrow = CSS.slice(CSS.indexOf(".mk-eyebrow {"));
    expect(eyebrow).toContain(".mk-eyebrow::before");
    expect(eyebrow.slice(0, 800)).toContain("background: var(--mk-brass)");
  });

  it("kennt die Bühnen-, Unterlagen- und Trennerbausteine", () => {
    for (const cls of [
      ".mk-stage",
      ".mk-paper",
      ".mk-mat",
      ".mk-brass-rule",
      ".mk-blueprint-inverse",
      ".mk-rail",
      ".mk-exhibit",
      ".mk-exhibit__index",
      ".mk-exhibit__claim",
      ".mk-exhibit__source",
    ]) {
      expect(CSS, `${cls} fehlt`).toContain(cls);
    }
  });

  it("markiert die aktive Navigation mit einem Messingstrich statt einer Fläche", () => {
    expect(CSS).toContain('.mk-navlink[data-active="true"]::after');
  });
});

describe("Blue-Brass Designebene — Motion-Governance", () => {
  it("schaltet Bewegung bei reduzierter Bewegungspräferenz ab", () => {
    expect(CSS).toContain("@media (prefers-reduced-motion: reduce)");
    expect(CSS).toContain("@media (prefers-reduced-motion: no-preference)");
  });

  it("bindet die Hover-Geste an feine Zeiger", () => {
    // Auf Touch gäbe es sonst einen Zustand, den niemand auslöst und der
    // nach dem Tippen hängen bleibt.
    expect(CSS).toContain("@media (hover: hover) and (pointer: fine)");
  });

  it("führt keine endlose dekorative Schleife", () => {
    // `infinite` ist auf einer Prüfoberfläche ein Anti-Pattern: Bewegung ohne
    // Informationswert, die nie zur Ruhe kommt.
    expect(CSS).not.toMatch(/animation:[^;]*infinite/);
  });
});
