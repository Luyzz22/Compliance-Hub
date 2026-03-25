"use client";

import React from "react";

import { useWorkspaceMode } from "@/hooks/useWorkspaceMode";

export type WorkspaceShellModeBannerViewProps = {
  loading: boolean;
  workspaceMode: "production" | "demo" | "playground";
  modeLabel: string;
  modeHint: string;
  docsUrl: string;
};

/**
 * Präsentation: Demo / Playground vs. Produktiv (ohne Hook, für einmaliges useWorkspaceMode in der Shell).
 */
export function WorkspaceShellModeBannerView({
  loading,
  workspaceMode,
  modeLabel,
  modeHint,
  docsUrl,
}: WorkspaceShellModeBannerViewProps) {
  if (loading || workspaceMode === "production") {
    return null;
  }

  return (
    <div
      className="mb-4 rounded-lg border border-amber-200/90 bg-amber-50/95 px-3 py-2 text-xs leading-relaxed text-amber-950 shadow-sm"
      role="status"
      data-testid="workspace-shell-mode-banner"
    >
      <span className="font-semibold">{modeLabel}</span>
      <span className="text-amber-900/90"> — {modeHint}</span>
      {docsUrl ? (
        <>
          {" "}
          <a
            href={docsUrl}
            className="font-medium text-amber-950 underline decoration-amber-600/50 underline-offset-2 hover:decoration-amber-800"
            target="_blank"
            rel="noreferrer"
          >
            Technische Doku
          </a>
        </>
      ) : null}
    </div>
  );
}

type Props = {
  tenantId: string;
};

/**
 * Dezenter Hinweis in der Mandanten-Shell: Demo / Playground vs. Produktiv.
 */
export function WorkspaceShellModeBanner({ tenantId }: Props) {
  const mode = useWorkspaceMode(tenantId);
  return (
    <WorkspaceShellModeBannerView
      loading={mode.loading}
      workspaceMode={mode.workspaceMode}
      modeLabel={mode.modeLabel}
      modeHint={mode.modeHint}
      docsUrl={mode.docsUrl}
    />
  );
}
