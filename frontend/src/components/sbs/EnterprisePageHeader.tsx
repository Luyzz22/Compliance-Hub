import Link from "next/link";
import React from "react";

import {
  CH_BREADCRUMB_CURRENT,
  CH_BREADCRUMB_LINK,
  CH_BREADCRUMB_SEPARATOR,
  CH_EYEBROW,
  CH_PAGE_SUB,
  CH_PAGE_TITLE,
} from "@/lib/boardLayout";

export type BreadcrumbItem = {
  label: string;
  href?: string;
};

export type EnterprisePageHeaderProps = {
  /** Kurzlabel über der H1, z. B. „Board" oder „Tenant" */
  eyebrow?: string;
  title: string;
  description?: React.ReactNode;
  /** Primäre Aktionen rechts (Buttons/Links) */
  actions?: React.ReactNode;
  /** Unter der Beschreibung: z. B. Sekundärnavigation */
  below?: React.ReactNode;
  /** Optional breadcrumbs above the eyebrow. */
  breadcrumbs?: BreadcrumbItem[];
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
  breadcrumbs,
}: EnterprisePageHeaderProps) {
  return (
    <header className="mb-8 border-b border-slate-200/80 pb-8">
      {breadcrumbs && breadcrumbs.length > 0 ? (
        <nav aria-label="Breadcrumb" className="mb-3 flex items-center gap-1.5">
          {breadcrumbs.map((crumb, i) => {
            const isLast = i === breadcrumbs.length - 1;
            return (
              <React.Fragment key={crumb.label}>
                {i > 0 ? (
                  <span className={CH_BREADCRUMB_SEPARATOR} aria-hidden>
                    /
                  </span>
                ) : null}
                {crumb.href && !isLast ? (
                  <Link href={crumb.href} className={CH_BREADCRUMB_LINK}>
                    {crumb.label}
                  </Link>
                ) : (
                  <span className={isLast ? CH_BREADCRUMB_CURRENT : CH_BREADCRUMB_LINK}>
                    {crumb.label}
                  </span>
                )}
              </React.Fragment>
            );
          })}
        </nav>
      ) : null}
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
