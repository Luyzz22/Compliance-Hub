import { describe, expect, it } from "vitest";

import {
  InvalidJsonBodyError,
  readBoundedJsonBody,
  RequestBodyTooLargeError,
} from "@/lib/boundedJsonBody";

describe("readBoundedJsonBody", () => {
  it("parses a legitimate bounded object", async () => {
    const request = new Request("https://complywithai.de/api/example", {
      method: "POST",
      body: JSON.stringify({ scenario: "synthetic" }),
    });

    await expect(readBoundedJsonBody(request, 128)).resolves.toEqual({
      scenario: "synthetic",
    });
  });

  it("rejects an oversized declared content length before reading", async () => {
    const request = new Request("https://complywithai.de/api/example", {
      method: "POST",
      headers: { "content-length": "129" },
      body: "{}",
    });

    await expect(readBoundedJsonBody(request, 128)).rejects.toBeInstanceOf(
      RequestBodyTooLargeError,
    );
  });

  it("rejects an oversized chunked body while streaming", async () => {
    const encoder = new TextEncoder();
    const request = new Request("https://complywithai.de/api/example", {
      method: "POST",
      // Node requires duplex for a ReadableStream request body.
      duplex: "half",
      body: new ReadableStream<Uint8Array>({
        start(controller) {
          controller.enqueue(encoder.encode('{"value":"'));
          controller.enqueue(encoder.encode("x".repeat(256)));
          controller.enqueue(encoder.encode('"}'));
          controller.close();
        },
      }),
    } as RequestInit & { duplex: "half" });

    await expect(readBoundedJsonBody(request, 128)).rejects.toBeInstanceOf(
      RequestBodyTooLargeError,
    );
  });

  it("rejects invalid JSON within the size limit", async () => {
    const request = new Request("https://complywithai.de/api/example", {
      method: "POST",
      body: "not-json",
    });

    await expect(readBoundedJsonBody(request, 128)).rejects.toBeInstanceOf(
      InvalidJsonBodyError,
    );
  });
});
