"use client";

import type { ReactNode } from "react";

import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import type { BreadcrumbItem } from "@/components/sbs/EnterprisePageHeader";
import {
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_SECTION_LABEL,
  CH_SHELL,
} from "@/lib/boardLayout";

export interface GovernanceWorkspaceTab {
  id: string;
  label: string;
  content: ReactNode;
}

export interface GovernanceWorkspaceLayoutProps {
  title: string;
  eyebrow?: string;
  /** Run-Status (z. B. draft | in_review | completed) — für Semantik / Tests, nicht zwingend sichtbar. */
  status: string;
  /** Vollständiger Block unter der H1 (Session, StatusBadge, Kontextzeilen). */
  headerDescription: ReactNode;
  breadcrumbs?: BreadcrumbItem[];
  headerActions?: ReactNode;
  tabs: GovernanceWorkspaceTab[];
  activeTabId: string;
  onTabChange: (tabId: string) => void;
  tablistAriaLabel?: string;
  toast?: { kind: "success" | "error"; text: string } | null;
  /** Metadaten-Karte (z. B. dl-Grid) — frei komponierbar. */
  metadataSection?: ReactNode;
  actionError?: ReactNode;
  /** Standard-Aktionen; optional, damit andere Workspaces eigene Buttons setzen können. */
  onStatusChange?: () => void | Promise<void>;
  onComplete?: () => void | Promise<void>;
  onExport?: () => void | Promise<void>;
  statusChangeDisabled?: boolean;
  completeDisabled?: boolean;
  exportDisabled?: boolean;
  busyAction?: "review" | "complete" | "export" | null;
  /** Button-Texte (deutsch, überschreibbar). */
  labels?: {
    statusChange?: string;
    statusChangeLoading?: string;
    complete?: string;
    completeLoading?: string;
    export?: string;
    exportLoading?: string;
  };
}

/**
 * Generische Shell für mandantenbezogene Governance-Workspaces (Tabs, Status, Aktionen).
 * Domain-Logik bleibt in Feature-Clients; dieses Layout nur Struktur & wiederkehrende UX.
 */
export function GovernanceWorkspaceLayout({
  title,
  eyebrow,
  status,
  headerDescription,
  breadcrumbs,
  headerActions,
  tabs,
  activeTabId,
  onTabChange,
  tablistAriaLabel = "Workspace-Bereiche",
  toast,
  metadataSection,
  actionError,
  onStatusChange,
  onComplete,
  onExport,
  statusChangeDisabled,
  completeDisabled,
  exportDisabled,
  busyAction,
  labels = {},
}: GovernanceWorkspaceLayoutProps) {
  const lb = {
    statusChange: labels.statusChange ?? "Status auf „In Review“ setzen",
    statusChangeLoading: labels.statusChangeLoading ?? "Bitte warten…",
    complete: labels.complete ?? "Run abschließen",
    completeLoading: labels.completeLoading ?? "Bitte warten…",
    export: labels.export ?? "Export (PDF)",
    exportLoading: labels.exportLoading ?? "Export…",
  };

  const hasDefaultActions = onStatusChange != null || onComplete != null || onExport != null;

  return (
    <div className={CH_SHELL} data-governance-workspace-status={status}>
      {toast ? (
        <div
          role="status"
          className={
            toast.kind === "error"
              ? "rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900 shadow-sm"
              : "rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900 shadow-sm"
          }
        >
          {toast.text}
        </div>
      ) : null}

      <EnterprisePageHeader
        eyebrow={eyebrow}
        title={title}
        description={headerDescription}
        breadcrumbs={breadcrumbs}
        actions={headerActions}
      />

      {metadataSection ? (
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Metadaten & Aktionen</p>
          <div className="mt-4">{metadataSection}</div>

          {actionError ? (
            <p className="mt-4 text-sm text-rose-800" role="alert">
              {actionError}
            </p>
          ) : null}

          {hasDefaultActions ? (
            <div className="mt-6 flex flex-wrap gap-2 border-t border-slate-200/80 pt-6">
              {onStatusChange ? (
                <button
                  type="button"
                  disabled={Boolean(statusChangeDisabled) || busyAction !== null}
                  onClick={() => void onStatusChange()}
                  className={`${CH_BTN_SECONDARY} disabled:pointer-events-none disabled:opacity-40`}
                >
                  {busyAction === "review" ? lb.statusChangeLoading : lb.statusChange}
                </button>
              ) : null}
              {onComplete ? (
                <button
                  type="button"
                  disabled={Boolean(completeDisabled) || busyAction !== null}
                  onClick={() => void onComplete()}
                  className={`${CH_BTN_PRIMARY} disabled:pointer-events-none disabled:opacity-40`}
                >
                  {busyAction === "complete" ? lb.completeLoading : lb.complete}
                </button>
              ) : null}
              {onExport ? (
                <button
                  type="button"
                  disabled={Boolean(exportDisabled) || busyAction !== null}
                  onClick={() => void onExport()}
                  className={`${CH_BTN_SECONDARY} disabled:pointer-events-none disabled:opacity-40`}
                >
                  {busyAction === "export" ? lb.exportLoading : lb.export}
                </button>
              ) : null}
            </div>
          ) : null}
        </article>
      ) : hasDefaultActions ? (
        <article className={CH_CARD}>
          {actionError ? (
            <p className="text-sm text-rose-800" role="alert">
              {actionError}
            </p>
          ) : null}
          <div className="mt-4 flex flex-wrap gap-2">
            {onStatusChange ? (
              <button
                type="button"
                disabled={Boolean(statusChangeDisabled) || busyAction !== null}
                onClick={() => void onStatusChange()}
                className={`${CH_BTN_SECONDARY} disabled:pointer-events-none disabled:opacity-40`}
              >
                {busyAction === "review" ? lb.statusChangeLoading : lb.statusChange}
              </button>
            ) : null}
            {onComplete ? (
              <button
                type="button"
                disabled={Boolean(completeDisabled) || busyAction !== null}
                onClick={() => void onComplete()}
                className={`${CH_BTN_PRIMARY} disabled:pointer-events-none disabled:opacity-40`}
              >
                {busyAction === "complete" ? lb.completeLoading : lb.complete}
              </button>
            ) : null}
            {onExport ? (
              <button
                type="button"
                disabled={Boolean(exportDisabled) || busyAction !== null}
                onClick={() => void onExport()}
                className={`${CH_BTN_SECONDARY} disabled:pointer-events-none disabled:opacity-40`}
              >
                {busyAction === "export" ? lb.exportLoading : lb.export}
              </button>
            ) : null}
          </div>
        </article>
      ) : null}

      <div
        className="flex flex-wrap gap-2 border-b border-slate-200/80 pb-1"
        role="tablist"
        aria-label={tablistAriaLabel}
      >
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={activeTabId === t.id}
            onClick={() => onTabChange(t.id)}
            className={
              activeTabId === t.id
                ? "rounded-xl bg-[var(--sbs-navy-mid)] px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[var(--sbs-navy-deep)]"
                : "rounded-xl px-4 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
            }
          >
            {t.label}
          </button>
        ))}
      </div>

      {tabs.find((t) => t.id === activeTabId)?.content ?? null}
    </div>
  );
}
