"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { createSelfAssessment, normalizeSessionId } from "@/lib/aiActSelfAssessmentApi";
import { tenantAiActSelfAssessmentDetailPath } from "@/lib/aiActSelfAssessmentRoutes";
import { CH_BTN_PRIMARY } from "@/lib/boardLayout";

interface Props {
  tenantId: string;
  className?: string;
}

export function StartNewSelfAssessmentButton({ tenantId, className }: Props) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onClick() {
    setError(null);
    setBusy(true);
    try {
      const res = await createSelfAssessment(tenantId, {});
      if (!res.ok) {
        setError(`${res.status}: ${res.message}`);
        return;
      }
      const row = res.data as Record<string, unknown>;
      const id = normalizeSessionId(row);
      if (!id) {
        setError("Antwort enthält keine session_id.");
        return;
      }
      router.push(tenantAiActSelfAssessmentDetailPath(id));
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col items-start gap-1">
      <button
        type="button"
        disabled={busy}
        onClick={() => void onClick()}
        className={
          className ?? `${CH_BTN_PRIMARY} disabled:pointer-events-none disabled:opacity-50`
        }
      >
        {busy ? "Wird erstellt…" : "Neues Self-Assessment starten"}
      </button>
      {error ? (
        <p className="max-w-prose text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
