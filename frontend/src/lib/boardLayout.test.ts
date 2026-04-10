import { describe, expect, it } from "vitest";

import {
  CH_AUTH_SHELL,
  CH_BADGE,
  CH_BREADCRUMB_CURRENT,
  CH_BREADCRUMB_LINK,
  CH_BREADCRUMB_SEPARATOR,
  CH_BTN_GHOST,
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_CARD_MUTED,
  CH_EYEBROW,
  CH_NAV_GROUP_LABEL,
  CH_PAGE_NAV_LINK,
  CH_PAGE_SUB,
  CH_PAGE_TITLE,
  CH_SECTION_LABEL,
  CH_SHELL,
  CH_SKELETON,
  chKpiStatusFromRatio,
} from "./boardLayout";

describe("boardLayout design tokens", () => {
  it("exports all core token strings", () => {
    const tokens = [
      CH_SHELL,
      CH_CARD,
      CH_CARD_MUTED,
      CH_PAGE_TITLE,
      CH_PAGE_SUB,
      CH_EYEBROW,
      CH_SECTION_LABEL,
      CH_PAGE_NAV_LINK,
      CH_BTN_PRIMARY,
      CH_BTN_SECONDARY,
      CH_BTN_GHOST,
    ];
    for (const t of tokens) {
      expect(typeof t).toBe("string");
      expect(t.length).toBeGreaterThan(0);
    }
  });

  it("exports new enterprise tokens", () => {
    const tokens = [
      CH_BREADCRUMB_LINK,
      CH_BREADCRUMB_CURRENT,
      CH_BREADCRUMB_SEPARATOR,
      CH_AUTH_SHELL,
      CH_NAV_GROUP_LABEL,
      CH_BADGE,
      CH_SKELETON,
    ];
    for (const t of tokens) {
      expect(typeof t).toBe("string");
      expect(t.length).toBeGreaterThan(0);
    }
  });

  it("chKpiStatusFromRatio returns correct status", () => {
    expect(chKpiStatusFromRatio(0.2).label).toBe("Kritisch");
    expect(chKpiStatusFromRatio(0.5).label).toBe("Beobachten");
    expect(chKpiStatusFromRatio(0.9).label).toBe("Im Plan");
  });
});
