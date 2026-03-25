import React from "react";

import {
  CH_EYEBROW,
  CH_PAGE_SUB,
  CH_PAGE_TITLE,
} from "@/lib/boardLayout";

export type EnterprisePageHeaderProps = {
  /** Kurzlabel über der H1, z. B. „Board“ oder „Tenant“ */
  eyebrow?: string;
  title: string;
  description?: React.ReactNode;
  /** Primäre Aktionen rechts (Buttons/Links) */
  actions?: React.ReactNode;
  /** Unter der Beschreibung: z. B. Sekundärnavigation */
  below?: React.ReactNode;
};

/**
 * Einheitlicher Seitenkopf (Apple-/SAP-Fiori-inspiriert: viel Weißraum, klare Hierarchie).
 */
export function EnterprisePageHeader({
  eyebrow,
  title,
  description,
  actions,
  below,
}: EnterprisePageHeaderProps) {
  return (
    <header className="mb-8 border-b border-slate-200/80 pb-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1">
          {eyebrow ? <p className={CH_EYEBROW}>{eyebrow}</p> : null}
          <h1 className={eyebrow ? `mt-2 ${CH_PAGE_TITLE}` : CH_PAGE_TITLE}>{title}</h1>
          {description != null && description !== "" ? (
            <div className={CH_PAGE_SUB}>{description}</div>
          ) : null}
          {below ? <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2">{below}</div> : null}
        </div>
        {actions ? (
          <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>
        ) : null}
      </div>
    </header>
  );
}
