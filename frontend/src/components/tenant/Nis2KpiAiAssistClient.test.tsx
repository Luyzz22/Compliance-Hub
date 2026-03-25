import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { Nis2KpiAiAssistClient } from "./Nis2KpiAiAssistClient";

describe("Nis2KpiAiAssistClient", () => {
  const saved = {
    llm: process.env.NEXT_PUBLIC_FEATURE_LLM_ENABLED,
    kpi: process.env.NEXT_PUBLIC_FEATURE_LLM_KPI_SUGGESTIONS,
  };

  beforeEach(() => {
    process.env.NEXT_PUBLIC_FEATURE_LLM_ENABLED = "1";
    process.env.NEXT_PUBLIC_FEATURE_LLM_KPI_SUGGESTIONS = "1";
  });

  afterEach(() => {
    if (saved.llm === undefined) delete process.env.NEXT_PUBLIC_FEATURE_LLM_ENABLED;
    else process.env.NEXT_PUBLIC_FEATURE_LLM_ENABLED = saved.llm;
    if (saved.kpi === undefined) delete process.env.NEXT_PUBLIC_FEATURE_LLM_KPI_SUGGESTIONS;
    else process.env.NEXT_PUBLIC_FEATURE_LLM_KPI_SUGGESTIONS = saved.kpi;
  });

  it("shows KPI assist UI when flags enabled", () => {
    render(<Nis2KpiAiAssistClient aiSystemId="sys-1" />);
    expect(screen.getByRole("button", { name: /KI-Vorschlag holen/i })).toBeTruthy();
    expect(screen.getByPlaceholderText(/Runbooks/i)).toBeTruthy();
  });

  it("hides when KPI suggestion flag is off", () => {
    process.env.NEXT_PUBLIC_FEATURE_LLM_KPI_SUGGESTIONS = "0";
    const { container } = render(<Nis2KpiAiAssistClient aiSystemId="sys-1" />);
    expect(container.firstChild).toBeNull();
  });
});
