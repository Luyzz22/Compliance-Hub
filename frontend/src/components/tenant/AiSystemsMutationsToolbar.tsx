"use client";

import React from "react";

import { useWorkspaceMode } from "@/hooks/useWorkspaceMode";
import { AiSystemsImportPanel } from "@/components/tenant/AiSystemsImportPanel";
import { CH_BTN_PRIMARY } from "@/lib/boardLayout";

type Props = {
  tenantId: string;
};

/**
 * Register-Kopf: Import + Platzhalter „Neues System“ mit Demo-Schreibschutz.
 */
export function AiSystemsMutationsToolbar({ tenantId }: Props) {
  const { mutationsBlocked, modeHint } = useWorkspaceMode(tenantId);

  return (
    <div className="flex flex-wrap items-center gap-3">
      <AiSystemsImportPanel mutationsBlocked={mutationsBlocked} blockedHint={modeHint} />
      <button
        type="button"
        className={`${CH_BTN_PRIMARY} text-sm disabled:cursor-not-allowed disabled:opacity-50`}
        disabled={mutationsBlocked}
        title={
          mutationsBlocked
            ? modeHint || "Schreibgeschützter Demo-Mandant"
            : "Anlage folgt (API bereits vorhanden)"
        }
        data-testid="ai-systems-new-placeholder"
      >
        {mutationsBlocked ? "Neues System (Demo)" : "Neues System"}
      </button>
    </div>
  );
}
