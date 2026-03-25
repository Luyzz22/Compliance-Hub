import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { KpiExplainButton } from "./KpiExplainButton";

describe("KpiExplainButton", () => {
  const saved = {
    llm: process.env.NEXT_PUBLIC_FEATURE_LLM_ENABLED,
    ex: process.env.NEXT_PUBLIC_FEATURE_LLM_EXPLAIN,
  };

  beforeEach(() => {
    process.env.NEXT_PUBLIC_FEATURE_LLM_ENABLED = "1";
    process.env.NEXT_PUBLIC_FEATURE_LLM_EXPLAIN = "1";
  });

  afterEach(() => {
    if (saved.llm === undefined) delete process.env.NEXT_PUBLIC_FEATURE_LLM_ENABLED;
    else process.env.NEXT_PUBLIC_FEATURE_LLM_ENABLED = saved.llm;
    if (saved.ex === undefined) delete process.env.NEXT_PUBLIC_FEATURE_LLM_EXPLAIN;
    else process.env.NEXT_PUBLIC_FEATURE_LLM_EXPLAIN = saved.ex;
    vi.restoreAllMocks();
  });

  it("renders explain trigger when LLM flags are on", () => {
    render(
      <KpiExplainButton
        request={{ kpi_key: "test_kpi", current_value: 50, value_is_percent: true }}
      />
    );
    expect(screen.getByRole("button", { name: /bedeutet/i })).toBeTruthy();
  });

  it("renders nothing when explain flag is off", () => {
    process.env.NEXT_PUBLIC_FEATURE_LLM_EXPLAIN = "0";
    const { container } = render(
      <KpiExplainButton request={{ kpi_key: "x" }} />
    );
    expect(container.firstChild).toBeNull();
  });
});
