import { describe, expect, it } from "vitest";

import {
  ACTION_PLAN,
  AI_SYSTEM_REGISTER,
  BOARD_KPIS,
  CONTROL_STATUS,
  FRAMEWORKS,
  FRAMEWORK_COVERAGE,
  MAPPED_CONTROLS,
  NIS2_RISKS,
} from "./demoData";

/**
 * Die Demo-Daten tragen sämtliche Produktvisualisierungen der Website.
 * Inkonsistenzen fallen dort nicht auf, wirken aber unglaubwürdig — deshalb
 * werden die Zusammenhänge hier festgehalten.
 */
describe("Marketing-Demodaten", () => {
  it("verteilt den Kontrollstatus vollständig auf die aktiven Controls", () => {
    const sum =
      CONTROL_STATUS.compliant + CONTROL_STATUS.atRisk + CONTROL_STATUS.actionRequired;
    expect(sum).toBe(CONTROL_STATUS.total);
  });

  it("hält die Board-Kennzahlen in einem plausiblen Wertebereich", () => {
    for (const value of [BOARD_KPIS.readinessScore, BOARD_KPIS.evidenceCoverage]) {
      expect(value).toBeGreaterThan(0);
      expect(value).toBeLessThanOrEqual(100);
    }
    expect(BOARD_KPIS.aiSystemsHighRisk).toBeLessThanOrEqual(BOARD_KPIS.aiSystems);
  });

  it("zählt so viele Hochrisiko-Systeme im Registerauszug wie ausgewiesen", () => {
    const highRisk = AI_SYSTEM_REGISTER.filter((system) => system.riskClass === "hoch");
    expect(highRisk.length).toBeLessThanOrEqual(BOARD_KPIS.aiSystemsHighRisk);
    for (const system of AI_SYSTEM_REGISTER) {
      expect(system.riskBasis.trim()).not.toBe("");
      expect(system.owner.trim()).not.toBe("");
    }
  });

  it("führt jedes Control über alle sechs Regelwerke mit konkreter Fundstelle", () => {
    const frameworkIds = new Set(FRAMEWORKS.map((framework) => framework.id));
    for (const control of MAPPED_CONTROLS) {
      expect(control.mappings).toHaveLength(FRAMEWORKS.length);
      for (const mapping of control.mappings) {
        expect(frameworkIds.has(mapping.framework)).toBe(true);
        expect(mapping.reference.trim()).not.toBe("");
      }
    }
  });

  it("deckt in der Regelwerksübersicht genau die geführten Regelwerke ab", () => {
    expect(FRAMEWORK_COVERAGE.map((entry) => entry.id).sort()).toEqual(
      FRAMEWORKS.map((framework) => framework.id).sort(),
    );
    for (const entry of FRAMEWORK_COVERAGE) {
      expect(entry.open).toBeLessThanOrEqual(entry.controls);
    }
  });

  it("weist jede Maßnahme mit Owner, Frist und Regelwerksbezug aus", () => {
    for (const action of ACTION_PLAN) {
      expect(action.owner.trim()).not.toBe("");
      expect(action.ownerRole.trim()).not.toBe("");
      expect(action.framework.trim()).not.toBe("");
      expect(action.reference.trim()).not.toBe("");
      expect(action.due).toMatch(/^\d{2}\.\d{2}\.\d{4}$/);
    }
  });

  it("stimmt die Zahl der NIS2-Risiken mit hoher Bewertung mit der Board-Kennzahl ab", () => {
    const highPlus = NIS2_RISKS.filter((risk) => risk.impact * risk.likelihood >= 15);
    expect(highPlus).toHaveLength(BOARD_KPIS.nis2HighRisks);
  });
});
