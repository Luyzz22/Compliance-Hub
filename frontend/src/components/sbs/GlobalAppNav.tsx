"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React, { useEffect, useRef, useState } from "react";

import { isAdvisorNavEnabled } from "@/lib/api";
import {
  ADMIN_NAV_ITEMS,
  BOARD_NAV_ITEMS,
  REPORTING_NAV_ITEMS,
  WORKSPACE_NAV_ITEMS,
} from "@/lib/appNavConfig";

import { GlobalWorkspaceEvidenceNavBlock } from "./GlobalWorkspaceEvidenceNavBlock";

function navLinkClass(active: boolean): string {
  return [
    "rounded-lg px-2.5 py-2 text-xs font-medium transition md:text-[0.8rem]",
    active
      ? "bg-cyan-50 text-cyan-900 ring-1 ring-cyan-200/80"
      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
  ].join(" ");
}

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
        className={`flex h-9 w-9 items-center justify-center rounded-lg transition ${
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

export function GlobalAppNav() {
  const pathname = usePathname();
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
    <nav
      className="flex flex-wrap items-center justify-end gap-x-1 gap-y-1 md:gap-x-2"
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

      <Dropdown label="Reporting" active={reportingActive}>
        {REPORTING_NAV_ITEMS.map((item) => (
          <DropdownLink key={item.href} href={item.href}>
            {item.label}
          </DropdownLink>
        ))}
      </Dropdown>

      <Link href="/ai-systems" className={navLinkClass(aiSystemsActive)}>
        AI Systems
      </Link>

      <Link href="/incidents" className={navLinkClass(incidentsActive)}>
        Incidents
      </Link>

      {showAdvisorNav ? (
        <Link href="/advisor" className={navLinkClass(advisorActive)}>
          Advisor
        </Link>
      ) : null}

      <Dropdown label="Admin" active={adminActive}>
        {ADMIN_NAV_ITEMS.map((item) => (
          <DropdownLink key={item.href} href={item.href}>
            {item.label}
          </DropdownLink>
        ))}
      </Dropdown>

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
  );
}

