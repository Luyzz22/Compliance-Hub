"use client";

import React, { useState } from "react";

import { CH_BTN_PRIMARY } from "@/lib/boardLayout";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.COMPLIANCEHUB_API_BASE_URL ||
  "http://localhost:8000";
const API_KEY =
  process.env.NEXT_PUBLIC_API_KEY ||
  process.env.COMPLIANCEHUB_API_KEY ||
  "tenant-overview-key";
const TENANT_ID =
  process.env.NEXT_PUBLIC_TENANT_ID ||
  process.env.COMPLIANCEHUB_TENANT_ID ||
  "tenant-overview-001";

export function PdfReportDownloadButton() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDownload() {
    setLoading(true);
    setError(null);
    try {
      const opaRole = process.env.NEXT_PUBLIC_OPA_USER_ROLE?.trim();
      const headers: Record<string, string> = {
        "x-api-key": API_KEY,
        "x-tenant-id": TENANT_ID,
      };
      if (opaRole) headers["x-opa-user-role"] = opaRole;

      const res = await fetch(
        `${API_BASE_URL}/api/v1/enterprise/board/pdf-report`,
        { headers },
      );

      if (res.status === 403) {
        setError(
          "Zugriff verweigert — PDF-Report erfordert BOARD_MEMBER, CISO oder TENANT_ADMIN Rolle.",
        );
        return;
      }
      if (!res.ok) {
        setError(`Download fehlgeschlagen (HTTP ${res.status})`);
        return;
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `board-report-${TENANT_ID}.html`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Download fehlgeschlagen",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <button
        onClick={handleDownload}
        disabled={loading}
        className={CH_BTN_PRIMARY}
      >
        {loading ? "Wird generiert…" : "📄 PDF/A-3 Board Report herunterladen"}
      </button>
      {error && (
        <p className="mt-2 text-sm text-red-600">{error}</p>
      )}
    </div>
  );
}
