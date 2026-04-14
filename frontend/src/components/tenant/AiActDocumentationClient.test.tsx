import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AiActDocumentationClient } from "./AiActDocumentationClient";

const mockList = vi.fn();
const mockDraft = vi.fn();
const mockPersist = vi.fn();
const mockDownload = vi.fn();

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    fetchAiActDocList: (...a: unknown[]) => mockList(...a),
    postAiActDocDraft: (...a: unknown[]) => mockDraft(...a),
    persistAiActDocSection: (...a: unknown[]) => mockPersist(...a),
    downloadAiActDocumentationMarkdown: (...a: unknown[]) => mockDownload(...a),
  };
});

describe("AiActDocumentationClient", () => {
  const saved = {
    docs: process.env.NEXT_PUBLIC_FEATURE_AI_ACT_DOCS,
    llm: process.env.NEXT_PUBLIC_FEATURE_LLM_ENABLED,
    leg: process.env.NEXT_PUBLIC_FEATURE_LLM_LEGAL_REASONING,
    rep: process.env.NEXT_PUBLIC_FEATURE_LLM_REPORT_ASSISTANT,
  };

  beforeEach(() => {
    process.env.NEXT_PUBLIC_FEATURE_AI_ACT_DOCS = "1";
    process.env.NEXT_PUBLIC_FEATURE_LLM_ENABLED = "1";
    process.env.NEXT_PUBLIC_FEATURE_LLM_LEGAL_REASONING = "1";
    process.env.NEXT_PUBLIC_FEATURE_LLM_REPORT_ASSISTANT = "1";
    mockList.mockResolvedValue({
      ai_system_id: "sys-1",
      items: [
        {
          section_key: "RISK_MANAGEMENT",
          default_title: "Risikomanagement",
          doc: null,
          status: "empty",
        },
        {
          section_key: "DATA_GOVERNANCE",
          default_title: "Daten-Governance",
          doc: null,
          status: "empty",
        },
        {
          section_key: "MONITORING_LOGGING",
          default_title: "Monitoring",
          doc: null,
          status: "empty",
        },
        {
          section_key: "HUMAN_OVERSIGHT",
          default_title: "Aufsicht",
          doc: null,
          status: "empty",
        },
        {
          section_key: "TECHNICAL_ROBUSTNESS",
          default_title: "Robustheit",
          doc: null,
          status: "empty",
        },
      ],
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
    if (saved.docs === undefined) delete process.env.NEXT_PUBLIC_FEATURE_AI_ACT_DOCS;
    else process.env.NEXT_PUBLIC_FEATURE_AI_ACT_DOCS = saved.docs;
    if (saved.llm === undefined) delete process.env.NEXT_PUBLIC_FEATURE_LLM_ENABLED;
    else process.env.NEXT_PUBLIC_FEATURE_LLM_ENABLED = saved.llm;
    if (saved.leg === undefined) delete process.env.NEXT_PUBLIC_FEATURE_LLM_LEGAL_REASONING;
    else process.env.NEXT_PUBLIC_FEATURE_LLM_LEGAL_REASONING = saved.leg;
    if (saved.rep === undefined) delete process.env.NEXT_PUBLIC_FEATURE_LLM_REPORT_ASSISTANT;
    else process.env.NEXT_PUBLIC_FEATURE_LLM_REPORT_ASSISTANT = saved.rep;
  });

  it("shows documentation UI and draft control when flags enabled", async () => {
    render(<AiActDocumentationClient aiSystemId="sys-1" />);
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /EU AI Act Dokumentation/i })).toBeTruthy();
    });
    expect(screen.getByRole("button", { name: /KI-Entwurf erzeugen/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Speichern/i })).toBeTruthy();
    expect(screen.getByRole("textbox", { name: /Markdown/i })).toBeTruthy();
  });

  it("hides when AI Act docs flag is off", () => {
    process.env.NEXT_PUBLIC_FEATURE_AI_ACT_DOCS = "0";
    const { container } = render(<AiActDocumentationClient aiSystemId="sys-1" />);
    expect(container.firstChild).toBeNull();
  });
});
