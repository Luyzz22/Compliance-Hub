import { afterEach, describe, expect, it, vi } from "vitest";

/**
 * Ausgabeformat je Zielplattform — geprüft am tatsächlich geladenen Config-Objekt,
 * nicht am Quelltext.
 *
 * Zwei Plattformen, zwei Anforderungen, die sich ausschließen:
 *
 * - Der Hetzner-Container kopiert `.next/standalone`. Fehlt `standalone`, startet
 *   das Image nicht.
 * - Der Vercel-Plattformadapter bricht mit `standalone` in `onBuildComplete` ab
 *   (`ENOENT … .next/next-server.js.nft.json`). Genau das hat jeden Vercel-Build
 *   seit PR #290 scheitern lassen, verdeckt von der Plattformsperre im Gate.
 */
async function loadConfig(vercel: string | undefined) {
  vi.resetModules();
  if (vercel === undefined) {
    vi.stubEnv("VERCEL", "");
  } else {
    vi.stubEnv("VERCEL", vercel);
  }
  const { default: config } = await import("../../next.config");
  return config;
}

describe("next.config — Ausgabeformat", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("baut den Container standalone", async () => {
    const config = await loadConfig(undefined);
    expect(config.output).toBe("standalone");
  });

  it("überlässt die Ausgabe auf Vercel dem Plattformadapter", async () => {
    const config = await loadConfig("1");
    expect(config.output).toBeUndefined();
  });
});
