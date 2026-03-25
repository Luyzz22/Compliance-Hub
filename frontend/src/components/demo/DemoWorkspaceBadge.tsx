"use client";

import React from "react";

import { useWorkspaceMode } from "@/hooks/useWorkspaceMode";

/**
 * Kompaktes Badge in der Mandanten-Shell: Label aus Workspace-Meta (Server-Vertrag).
 */
export function DemoWorkspaceBadge({ tenantId }: { tenantId: string }) {
  const { loading, isDemo, modeLabel, modeHint } = useWorkspaceMode(tenantId);

  if (loading || !isDemo) {
    return null;
  }

  return (
    <span
      className="inline-flex max-w-full items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-2.5 py-0.5 text-[0.65rem] font-bold uppercase tracking-wide text-amber-950"
      title={modeHint}
    >
      <span aria-hidden>●</span>
      <span className="normal-case">{modeLabel}</span>
    </span>
  );
}
