"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React, { useCallback, useEffect, useRef, useState } from "react";

import {
  useCanSeeAdmin,
  useCanSeeAiSystems,
  useCanSeeReporting,
} from "@/hooks/useUserRole";
import { isAdvisorNavEnabled } from "@/lib/api";
import {
  ADMIN_NAV_ITEMS,
  BOARD_NAV_ITEMS,
  REPORTING_NAV_ITEMS,
  WORKSPACE_NAV_ITEMS,
} from "@/lib/appNavConfig";

import { GlobalWorkspaceEvidenceNavBlock } from "./GlobalWorkspaceEvidenceNavBlock";
import { UpgradeModal } from "./UpgradeModal";

/* ── Feature-gating helpers ────────────────────────────────────────── */

/** Feature keys that are gated per plan. Items not listed here are ungated. */
const NAV_FEATURE_GATES: Record<string, { feature: string; requiredPlan: string }> = {
  "/board/datev-export": { feature: "datev_export", requiredPlan: "Professional" },
  "/board/xrechnung-export": { feature: "xrechnung", requiredPlan: "Enterprise" },
  "/board/gap-analysis": { feature: "rag_gap_analysis", requiredPlan: "Professional" },
};

function isFeatureGated(href: string): boolean {
  return href in NAV_FEATURE_GATES;
}

function requiredPlanLabel(href: string): string {
  return NAV_FEATURE_GATES[href]?.requiredPlan ?? "Professional";
}

/* ── Shared styles ─────────────────────────────────────────────────── */

function navLinkClass(active: boolean): string {
  return [
    "rounded-lg px-2.5 py-2 text-xs font-medium transition md:text-[0.8rem]",
    active
      ? "bg-cyan-50 text-cyan-900 ring-1 ring-cyan-200/80"
      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
  ].join(" ");
}

/* ── Icons ─────────────────────────────────────────────────────────── */

function LockIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden {...props}>
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0110 0v4" />
    </svg>
  );
}

function HamburgerIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden {...props}>
      <line x1="3" y1="6" x2="21" y2="6" />
      <line x1="3" y1="12" x2="21" y2="12" />
      <line x1="3" y1="18" x2="21" y2="18" />
    </svg>
  );
}

function CloseIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden {...props}>
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

/* ── Sub-components ────────────────────────────────────────────────── */

function Dropdown({
  label,
  active,
  children,
}: {
  label: string;
  active: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("click", onDoc);
    return () => document.removeEventListener("click", onDoc);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="true"
        onClick={() => setOpen((o) => !o)}
        className={navLinkClass(active)}
      >
        {label}
        <span className="ml-0.5 text-[0.65rem] opacity-70" aria-hidden>
          ▾
        </span>
      </button>
      {open ? (
        <div
          className="absolute right-0 top-full z-50 mt-1 min-w-[14rem] rounded-xl border border-slate-200/90 bg-white py-1 shadow-lg shadow-slate-200/50 md:left-0 md:right-auto"
          role="menu"
        >
          {children}
        </div>
      ) : null}
    </div>
  );
}

function DropdownLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const active = pathname === href || pathname.startsWith(`${href}/`);
  return (
    <Link
      href={href}
      role="menuitem"
      className={`block px-3 py-2 text-sm no-underline ${
        active
          ? "bg-cyan-50 font-semibold text-cyan-900"
          : "text-slate-700 hover:bg-slate-50"
      }`}
    >
      {children}
    </Link>
  );
}

/** A gated dropdown item: shows a lock icon and triggers an upgrade modal on click. */
function GatedDropdownItem({
  href,
  children,
  onUpgrade,
}: {
  href: string;
  children: React.ReactNode;
  onUpgrade: (href: string) => void;
}) {
  return (
    <button
      type="button"
      role="menuitem"
      onClick={() => onUpgrade(href)}
      className="flex w-full items-center gap-2 px-3 py-2 text-sm text-slate-400 hover:bg-slate-50"
    >
      <LockIcon className="h-3.5 w-3.5 shrink-0" />
      <span>{children}</span>
    </button>
  );
}

function DropdownSeparator({ label }: { label: string }) {
  return (
    <div className="border-t border-slate-100 px-3 pb-1 pt-2 text-[0.6rem] font-bold uppercase tracking-wider text-slate-400">
      {label}
    </div>
  );
}

function SettingsIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      {...props}
    >
      <circle cx="12" cy="12" r="3" />
      <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
    </svg>
  );
}

function UserIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      {...props}
    >
      <circle cx="12" cy="8" r="4" />
      <path d="M20 21a8 8 0 1 0-16 0" />
    </svg>
  );
}

function UserMenu({ active }: { active: boolean }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("click", onDoc);
    return () => document.removeEventListener("click", onDoc);
  }, []);

  return (
    <div className="relative ml-0.5 md:ml-1" ref={ref}>
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="true"
        aria-label="Konto-Menü"
        onClick={() => setOpen((o) => !o)}
        className={`flex h-11 w-11 items-center justify-center rounded-lg transition md:h-9 md:w-9 ${
          active
            ? "bg-cyan-50 text-cyan-900 ring-1 ring-cyan-200/80"
            : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
        }`}
      >
        <UserIcon className="h-5 w-5" />
      </button>
      {open ? (
        <div
          className="absolute right-0 top-full z-50 mt-1 min-w-[14rem] rounded-xl border border-slate-200/90 bg-white py-1 shadow-lg shadow-slate-200/50"
          role="menu"
        >
          <DropdownSeparator label="Konto" />
          <DropdownLink href="/auth/login">Anmelden</DropdownLink>
          <DropdownLink href="/auth/register">Registrieren</DropdownLink>
          <DropdownLink href="/auth/profile">Profil</DropdownLink>
        </div>
      ) : null}
    </div>
  );
}

/* ── Mobile drawer ─────────────────────────────────────────────────── */

function MobileNavContent({
  onClose,
  showReporting,
  showAdmin,
  showAiSystems,
  showAdvisorNav,
  onUpgrade,
}: {
  onClose: () => void;
  showReporting: boolean;
  showAdmin: boolean;
  showAiSystems: boolean;
  showAdvisorNav: boolean;
  onUpgrade: (href: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1 p-4">
      <Link href="/" onClick={onClose} className="block rounded-lg px-3 py-3 text-sm font-medium text-slate-700 hover:bg-slate-100">
        Start
      </Link>

      <DropdownSeparator label="Board" />
      {BOARD_NAV_ITEMS.map((item) => (
        <Link key={item.href} href={item.href} onClick={onClose} className="block rounded-lg px-3 py-3 text-sm text-slate-700 hover:bg-slate-50">
          {item.label}
        </Link>
      ))}

      <DropdownSeparator label="Workspace" />
      {WORKSPACE_NAV_ITEMS.map((item) => (
        <Link key={item.href} href={item.href} onClick={onClose} className="block rounded-lg px-3 py-3 text-sm text-slate-700 hover:bg-slate-50">
          {item.label}
        </Link>
      ))}

      {showReporting ? (
        <>
          <DropdownSeparator label="Reporting" />
          {REPORTING_NAV_ITEMS.map((item) =>
            isFeatureGated(item.href) ? (
              <button
                key={item.href}
                type="button"
                onClick={() => onUpgrade(item.href)}
                className="flex items-center gap-2 rounded-lg px-3 py-3 text-sm text-slate-400 hover:bg-slate-50"
              >
                <LockIcon className="h-3.5 w-3.5" />
                {item.label}
              </button>
            ) : (
              <Link key={item.href} href={item.href} onClick={onClose} className="block rounded-lg px-3 py-3 text-sm text-slate-700 hover:bg-slate-50">
                {item.label}
              </Link>
            ),
          )}
        </>
      ) : null}

      {showAiSystems ? (
        <Link href="/ai-systems" onClick={onClose} className="block rounded-lg px-3 py-3 text-sm text-slate-700 hover:bg-slate-100">
          AI Systems
        </Link>
      ) : null}

      <Link href="/incidents" onClick={onClose} className="block rounded-lg px-3 py-3 text-sm text-slate-700 hover:bg-slate-100">
        Incidents
      </Link>

      {showAdvisorNav ? (
        <Link href="/advisor" onClick={onClose} className="block rounded-lg px-3 py-3 text-sm text-slate-700 hover:bg-slate-100">
          Advisor
        </Link>
      ) : null}

      {showAdmin ? (
        <>
          <DropdownSeparator label="Admin" />
          {ADMIN_NAV_ITEMS.map((item) => (
            <Link key={item.href} href={item.href} onClick={onClose} className="block rounded-lg px-3 py-3 text-sm text-slate-700 hover:bg-slate-50">
              {item.label}
            </Link>
          ))}
        </>
      ) : null}

      <DropdownSeparator label="Konto" />
      <Link href="/auth/login" onClick={onClose} className="block rounded-lg px-3 py-3 text-sm text-slate-700 hover:bg-slate-50">
        Anmelden
      </Link>
      <Link href="/auth/register" onClick={onClose} className="block rounded-lg px-3 py-3 text-sm text-slate-700 hover:bg-slate-50">
        Registrieren
      </Link>
      <Link href="/auth/profile" onClick={onClose} className="block rounded-lg px-3 py-3 text-sm text-slate-700 hover:bg-slate-50">
        Profil
      </Link>
      <Link href="/settings" onClick={onClose} className="block rounded-lg px-3 py-3 text-sm text-slate-700 hover:bg-slate-50">
        Einstellungen
      </Link>
    </div>
  );
}

/* ── Main nav export ───────────────────────────────────────────────── */

export function GlobalAppNav() {
  const pathname = usePathname();

  // RBAC visibility
  const showAdmin = useCanSeeAdmin();
  const showReporting = useCanSeeReporting();
  const showAiSystems = useCanSeeAiSystems();

  // Mobile drawer
  const [mobileOpen, setMobileOpen] = useState(false);
  const mobileRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!mobileOpen) return;
    function onDoc(e: MouseEvent) {
      if (mobileRef.current && !mobileRef.current.contains(e.target as Node)) {
        setMobileOpen(false);
      }
    }
    document.addEventListener("click", onDoc);
    return () => document.removeEventListener("click", onDoc);
  }, [mobileOpen]);

  // Feature-gating upgrade modal
  const [upgradeHref, setUpgradeHref] = useState<string | null>(null);
  const handleUpgrade = useCallback((href: string) => {
    setUpgradeHref(href);
  }, []);

  const boardActive =
    pathname.startsWith("/board") &&
    !REPORTING_NAV_ITEMS.some(
      (r) => pathname === r.href || pathname.startsWith(`${r.href}/`),
    );
  const workspaceActive =
    pathname.startsWith("/tenant") || pathname.startsWith("/tenants");
  const homeActive = pathname === "/";
  const incidentsActive =
    pathname === "/incidents" || pathname.startsWith("/board/incidents");
  const settingsActive = pathname === "/settings";
  const advisorActive = pathname.startsWith("/advisor");
  const showAdvisorNav = isAdvisorNavEnabled();
  const reportingActive = REPORTING_NAV_ITEMS.some(
    (r) => pathname === r.href || pathname.startsWith(`${r.href}/`),
  );
  const adminActive = pathname.startsWith("/admin");
  const authActive = pathname.startsWith("/auth");
  const aiSystemsActive = pathname === "/ai-systems";

  return (
    <>
      {/* ── Mobile hamburger button (visible < md) ─────────────── */}
      <div className="relative md:hidden" ref={mobileRef}>
        <button
          type="button"
          aria-label={mobileOpen ? "Menü schließen" : "Menü öffnen"}
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen((o) => !o)}
          className="flex h-11 w-11 items-center justify-center rounded-lg text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
        >
          {mobileOpen ? <CloseIcon className="h-5 w-5" /> : <HamburgerIcon className="h-5 w-5" />}
        </button>
        {mobileOpen ? (
          <div
            className="fixed inset-x-0 top-16 z-50 max-h-[calc(100vh-4rem)] overflow-y-auto border-b border-slate-200/90 bg-white shadow-lg"
            role="navigation"
            aria-label="Mobile Navigation"
          >
            <MobileNavContent
              onClose={() => setMobileOpen(false)}
              showReporting={showReporting}
              showAdmin={showAdmin}
              showAiSystems={showAiSystems}
              showAdvisorNav={showAdvisorNav}
              onUpgrade={handleUpgrade}
            />
          </div>
        ) : null}
      </div>

      {/* ── Desktop nav (hidden < md) ──────────────────────────── */}
      <nav
        className="hidden flex-wrap items-center justify-end gap-x-1 gap-y-1 md:flex md:gap-x-2"
        aria-label="Hauptnavigation"
      >
        <Link href="/" className={navLinkClass(homeActive)}>
          Start
        </Link>

        <Dropdown label="Board" active={boardActive}>
          {BOARD_NAV_ITEMS.map((item) => (
            <DropdownLink key={item.href} href={item.href}>
              {item.label}
            </DropdownLink>
          ))}
        </Dropdown>

        <Dropdown label="Workspace" active={workspaceActive}>
          {WORKSPACE_NAV_ITEMS.map((item) => (
            <DropdownLink key={item.href} href={item.href}>
              {item.label}
            </DropdownLink>
          ))}
          <GlobalWorkspaceEvidenceNavBlock />
        </Dropdown>

        {showReporting ? (
          <Dropdown label="Reporting" active={reportingActive}>
            {REPORTING_NAV_ITEMS.map((item) =>
              isFeatureGated(item.href) ? (
                <GatedDropdownItem key={item.href} href={item.href} onUpgrade={handleUpgrade}>
                  {item.label}
                </GatedDropdownItem>
              ) : (
                <DropdownLink key={item.href} href={item.href}>
                  {item.label}
                </DropdownLink>
              ),
            )}
          </Dropdown>
        ) : null}

        {showAiSystems ? (
          <Link href="/ai-systems" className={navLinkClass(aiSystemsActive)}>
            AI Systems
          </Link>
        ) : null}

        <Link href="/incidents" className={navLinkClass(incidentsActive)}>
          Incidents
        </Link>

        {showAdvisorNav ? (
          <Link href="/advisor" className={navLinkClass(advisorActive)}>
            Advisor
          </Link>
        ) : null}

        {showAdmin ? (
          <Dropdown label="Admin" active={adminActive}>
            {ADMIN_NAV_ITEMS.map((item) => (
              <DropdownLink key={item.href} href={item.href}>
                {item.label}
              </DropdownLink>
            ))}
          </Dropdown>
        ) : null}

        <Link
          href="/settings"
          className={`ml-0.5 flex h-9 w-9 items-center justify-center rounded-lg transition md:ml-1 ${
            settingsActive
              ? "bg-cyan-50 text-cyan-900 ring-1 ring-cyan-200/80"
              : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
          }`}
          aria-label="Einstellungen"
          title="Einstellungen"
        >
          <SettingsIcon className="h-5 w-5" />
        </Link>

        <UserMenu active={authActive} />
      </nav>

      {/* Feature-gate upgrade modal */}
      {upgradeHref ? (
        <UpgradeModal
          planLabel={requiredPlanLabel(upgradeHref)}
          onClose={() => setUpgradeHref(null)}
        />
      ) : null}
    </>
  );
}

