import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  fetchAiActEvidenceEvents: vi.fn(),
  fetchAiActEvidenceEventDetail: vi.fn(),
  downloadAiActEvidenceExport: vi.fn(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchAiActEvidenceEvents: mocks.fetchAiActEvidenceEvents,
    fetchAiActEvidenceEventDetail: mocks.fetchAiActEvidenceEventDetail,
    downloadAiActEvidenceExport: mocks.downloadAiActEvidenceExport,
  };
});

import { AiActEvidencePageClient } from "./AiActEvidencePageClient";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const fetchAiActEvidenceEvents = mocks.fetchAiActEvidenceEvents;
const fetchAiActEvidenceEventDetail = mocks.fetchAiActEvidenceEventDetail;
const downloadAiActEvidenceExport = mocks.downloadAiActEvidenceExport;

describe("AiActEvidencePageClient", () => {
  it("renders list from mocked API", async () => {
    fetchAiActEvidenceEvents.mockResolvedValue({
      items: [
        {
          event_id: "audit:1",
          timestamp: "2026-01-01T12:00:00.000Z",
          event_type: "rag_query",
          tenant_id: "t1",
          user_role: "advisor",
          source: "rag",
          summary_de: "RAG-Test",
          confidence_level: "high",
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
    });

    render(<AiActEvidencePageClient tenantId="t1" />);

    await waitFor(() => {
      expect(fetchAiActEvidenceEvents).toHaveBeenCalled();
    });

    expect(screen.getByText("RAG-Test")).toBeTruthy();
    await waitFor(() => {
      expect(screen.getByText(/1 Treffer/)).toBeTruthy();
    });
  });

  it("applies filters: event_types and confidence in list request", async () => {
    fetchAiActEvidenceEvents.mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });

    render(<AiActEvidencePageClient tenantId="t-tenant" />);

    await waitFor(() => expect(fetchAiActEvidenceEvents).toHaveBeenCalled());

    const typeSelect = screen.getByRole("combobox", { name: /Ereignistyp/i });
    fireEvent.change(typeSelect, { target: { value: "rag" } });
    const confSelect = screen.getByRole("combobox", { name: /Konfidenz/i });
    fireEvent.change(confSelect, { target: { value: "low" } });

    fireEvent.click(screen.getByRole("button", { name: /Filter anwenden/i }));

    await waitFor(() => {
      expect(fetchAiActEvidenceEvents.mock.calls.length).toBeGreaterThanOrEqual(2);
    });

    const lastCall = fetchAiActEvidenceEvents.mock.calls.at(-1)?.[1] as {
      event_types?: string;
      confidence_level?: string;
    };
    expect(lastCall?.event_types).toBe("rag_query");
    expect(lastCall?.confidence_level).toBe("low");
  });

  it("detail drawer shows RAG-specific fields", async () => {
    fetchAiActEvidenceEvents.mockResolvedValue({
      items: [
        {
          event_id: "audit:rag-1",
          timestamp: "2026-02-01T10:00:00.000Z",
          event_type: "rag_query",
          tenant_id: "t1",
          user_role: "advisor",
          source: "rag",
          summary_de: "RAG Kurz",
          confidence_level: "medium",
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
    });

    fetchAiActEvidenceEventDetail.mockResolvedValue({
      event_id: "audit:rag-1",
      timestamp: "2026-02-01T10:00:00.000Z",
      event_type: "rag_query",
      tenant_id: "t1",
      user_role: "advisor",
      source: "rag",
      summary_de: "RAG Kurz",
      rag: {
        citation_doc_ids: ["eu-act-1"],
        tenant_guidance_citation_count: 2,
        confidence_level: "medium",
        trace_id: "trace-" + "a".repeat(40),
        span_id: "s1",
        citation_count: 3,
        query_sha256: "aa".repeat(32),
      },
    });

    render(<AiActEvidencePageClient tenantId="t1" />);

    await waitFor(() => screen.getByText("RAG Kurz"));

    fireEvent.click(screen.getByRole("button", { name: /Details zu audit:rag-1/i }));

    await waitFor(() => {
      expect(fetchAiActEvidenceEventDetail).toHaveBeenCalledWith("t1", "audit:rag-1");
    });

    const dialog = (await screen.findAllByRole("dialog")).find((el) =>
      within(el).queryByText("Ereignisdetails"),
    );
    expect(dialog).toBeTruthy();
    const panel = dialog!;
    expect(within(panel).getByText(/Mandanten-Leitfaden/)).toBeTruthy();
    expect(within(panel).getByText("eu-act-1")).toBeTruthy();
    expect(within(panel).getByText(/^trace-aa…aaaa$/)).toBeTruthy();
  });

  it("export uses current filters and format", async () => {
    const alertSpy = vi.spyOn(window, "alert").mockImplementation(() => {});
    const createMock = vi.fn(() => "blob:mock");
    const revokeMock = vi.fn();
    Object.defineProperty(globalThis.URL, "createObjectURL", {
      value: createMock,
      configurable: true,
      writable: true,
    });
    Object.defineProperty(globalThis.URL, "revokeObjectURL", {
      value: revokeMock,
      configurable: true,
      writable: true,
    });

    fetchAiActEvidenceEvents.mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });
    downloadAiActEvidenceExport.mockResolvedValue(new Blob(["{}"], { type: "application/json" }));

    render(<AiActEvidencePageClient tenantId="t-exp" />);

    await waitFor(() => expect(fetchAiActEvidenceEvents).toHaveBeenCalled());

    const typeSelect = screen.getByRole("combobox", { name: /Ereignistyp/i });
    fireEvent.change(typeSelect, { target: { value: "llm_violation" } });
    fireEvent.click(screen.getByRole("button", { name: /Filter anwenden/i }));

    await waitFor(() => expect(fetchAiActEvidenceEvents.mock.calls.length).toBeGreaterThanOrEqual(2));

    fireEvent.click(screen.getByRole("button", { name: /^Export$/i }));

    const exportDialog = await screen.findByRole("dialog", { name: /Evidence exportieren/i });
    fireEvent.change(within(exportDialog).getByRole("combobox"), {
      target: { value: "json" },
    });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    fireEvent.click(within(exportDialog).getByRole("button", { name: /Herunterladen/i }));

    await waitFor(() => {
      expect(downloadAiActEvidenceExport).toHaveBeenCalled();
    });

    clickSpy.mockRestore();

    expect(downloadAiActEvidenceExport).toHaveBeenCalledWith(
      "t-exp",
      "json",
      expect.objectContaining({
        event_types: "llm_contract_violation,llm_guardrail_block",
      }),
    );

    alertSpy.mockRestore();
    delete (globalThis.URL as unknown as { createObjectURL?: unknown }).createObjectURL;
    delete (globalThis.URL as unknown as { revokeObjectURL?: unknown }).revokeObjectURL;
  });
});
