import Link from "next/link";
import React from "react";

const nav = [
  { href: "/", label: "Start" },
  { href: "/board/kpis", label: "Board KPIs" },
  { href: "/board/nis2-kritis", label: "NIS2 / KRITIS" },
  { href: "/board/eu-ai-act-readiness", label: "EU AI Act" },
  { href: "/board/incidents", label: "Incidents" },
];

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

export function SbsHeader() {
  return (
    <header className="fixed top-0 left-0 right-0 z-[100] border-b border-white/10 bg-slate-950/85 shadow-sm shadow-black/20 backdrop-blur-xl backdrop-saturate-150">
      <div className="mx-auto flex h-16 min-w-0 max-w-7xl items-center justify-between gap-4 px-4 md:px-6">
        <Link href="/" className="group flex min-w-0 items-center gap-3 no-underline">
          <span
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400 to-teal-600 text-xs font-bold text-slate-950 shadow-md shadow-cyan-900/30"
            aria-hidden
          >
            CH
          </span>
          <span className="min-w-0 leading-tight">
            <span className="block truncate text-sm font-semibold tracking-tight text-white md:text-base">
              Compliance Hub
            </span>
            <span className="hidden text-[0.65rem] font-medium text-slate-400 sm:block">
              GRC · EU AI Act · NIS2 · ISO 42001
            </span>
          </span>
        </Link>
        <nav
          className="flex flex-wrap items-center justify-end gap-x-1 gap-y-1 md:gap-x-2"
          aria-label="Hauptnavigation"
        >
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-lg px-2 py-1.5 text-xs font-medium text-slate-300 transition hover:bg-white/10 hover:text-white md:px-2.5 md:text-[0.8rem]"
            >
              {item.label}
            </Link>
          ))}
          <Link
            href="/tenant/compliance-overview"
            className="ml-1 flex h-9 w-9 items-center justify-center rounded-lg text-slate-300 transition hover:bg-white/10 hover:text-white"
            aria-label="Einstellungen und Tenant-Bereich"
            title="Tenant / Einstellungen"
          >
            <SettingsIcon className="h-5 w-5" />
          </Link>
        </nav>
      </div>
    </header>
  );
}
