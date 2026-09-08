import { readFileSync, readdirSync, statSync } from "node:fs";
import { extname, join, resolve } from "node:path";

import { describe, expect, it } from "vitest";

/**
 * Ein Haus, eine Palette.
 *
 * Die Arbeitsflächen der Anwendung trugen über Jahre gewachsen sechs fremde
 * Farbfamilien: Cyan als Marke, dazu Violett, Indigo, Himmelblau, Blau und
 * Purpur als jeweils eigener Akzent pro Panel — „Wave 35" indigo, „Wave 36"
 * violett, Demo-Hinweise himmelblau. Jede für sich eine kleine Entscheidung,
 * zusammen eine Oberfläche, auf der Farbe nichts mehr bedeutet.
 *
 * Dieser Test hält den aufgeräumten Zustand. Er ist bewusst streng: die
 * billigste Stelle, eine Fremdfarbe zu stoppen, ist die erste.
 */

const SOURCE_ROOT = resolve(__dirname, "..");
const SOURCE_EXTENSIONS = new Set([".ts", ".tsx"]);

/** Familien, die es im Haus nicht gibt. */
const FOREIGN_FAMILIES = [
  "cyan",
  "violet",
  "indigo",
  "sky",
  "blue",
  "purple",
  "fuchsia",
  "pink",
  "rose",
  "teal",
  "orange",
  "lime",
];

function sourceFiles(directory: string): string[] {
  const found: string[] = [];
  for (const entry of readdirSync(directory)) {
    const path = join(directory, entry);
    if (statSync(path).isDirectory()) {
      found.push(...sourceFiles(path));
      continue;
    }
    // Der Test beschreibt die Regel und nennt die Familien beim Namen — er
    // darf sich nicht selbst als Fund melden.
    if (SOURCE_EXTENSIONS.has(extname(path)) && !path.includes("housePalette.test")) {
      found.push(path);
    }
  }
  return found;
}

const FILES = sourceFiles(SOURCE_ROOT);

describe("Hauspalette", () => {
  it("findet Quelldateien zum Prüfen", () => {
    // Ohne diese Zusicherung wäre ein kaputter Sammler ein grüner Test.
    expect(FILES.length).toBeGreaterThan(200);
  });

  for (const family of FOREIGN_FAMILIES) {
    it(`führt keine \`${family}\`-Utilities`, () => {
      const pattern = new RegExp(`\\b[a-z-]+-${family}-\\d{2,3}\\b`);
      const offenders: string[] = [];
      for (const file of FILES) {
        const content = readFileSync(file, "utf8");
        const match = content.match(pattern);
        if (match) {
          offenders.push(`${file.replace(SOURCE_ROOT, "src")}: ${match[0]}`);
        }
      }
      expect(offenders, offenders.join("\n")).toEqual([]);
    });
  }
});

/**
 * Die Rollen, auf denen die Ablösung aufsetzt. Fehlt eine davon, rendern die
 * ersetzten Klassen ohne Farbe — und zwar still, weil Tailwind eine unbekannte
 * Farbe einfach nicht ausgibt.
 */
describe("Hausrollen im Tailwind-Theme", () => {
  const globals = readFileSync(resolve(SOURCE_ROOT, "app/globals.css"), "utf8");

  it("registriert die Marken- und Messingrampe", () => {
    for (const shade of [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]) {
      expect(globals, `brand-${shade}`).toContain(`--color-brand-${shade}:`);
    }
    for (const shade of [50, 100, 200, 300, 400, 500, 600, 700, 800, 900]) {
      expect(globals, `brass-${shade}`).toContain(`--color-brass-${shade}:`);
    }
  });

  it("hält den Marken-Anker mit dem Schwesterprodukt gleich", () => {
    // #003856 ist in NormPilot Industrie `brand-700`. Der Wert ist die
    // Verwandtschaft — er darf nicht „ungefähr" stimmen.
    expect(globals).toContain("--color-brand-700: #003856;");
    expect(globals).toContain("--color-brass-400: #b98f42;");
  });

  it("führt die neutrale Skala als Graphit statt als Slate", () => {
    // Tailwinds Slate trägt Blauanteil und las neben der Petrol-Navy-Marke als
    // zweiter, konkurrierender Blauton.
    expect(globals).toContain("--color-slate-500: #61717c;");
    expect(globals).toContain("--color-slate-900: #161e23;");
  });

  it("führt die Statusrampen in den gedeckten Hauswerten", () => {
    expect(globals).toContain("--color-emerald-600: #0f6e4e;");
    expect(globals).toContain("--color-amber-600: #8a5a0b;");
    expect(globals).toContain("--color-red-600: #a32217;");
  });
});
