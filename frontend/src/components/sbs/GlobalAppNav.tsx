"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React, { useEffect, useRef, useState } from "react";

import {
  BOARD_NAV_ITEMS,
  WORKSPACE_NAV_ITEMS,
} from "@/lib/appNavConfig";

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

export function GlobalAppNav() {
  const pathname = usePathname();
  const boardActive = pathname.startsWith("/board");
  const workspaceActive = pathname.startsWith("/tenant");
  const homeActive = pathname === "/";
  const incidentsActive =
    pathname === "/incidents" || pathname.startsWith("/board/incidents");
  const settingsActive = pathname === "/settings";

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
      </Dropdown>

      <Link href="/incidents" className={navLinkClass(incidentsActive)}>
        Incidents
      </Link>

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
    </nav>
  );
}
