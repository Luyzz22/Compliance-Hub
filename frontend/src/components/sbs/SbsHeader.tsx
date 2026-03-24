import Link from "next/link";
import React from "react";

const nav = [
  { href: "/", label: "Start" },
  { href: "/board/kpis", label: "Board KPIs" },
  { href: "/board/nis2-kritis", label: "NIS2 / KRITIS" },
  { href: "/board/eu-ai-act-readiness", label: "EU AI Act" },
  { href: "/board/incidents", label: "Incidents" },
  { href: "/board/suppliers", label: "Supplier" },
  { href: "/tenant/compliance-overview", label: "Tenant" },
];

export function SbsHeader() {
  return (
    <header className="sbs-header-2026">
      <div className="sbs-header-inner">
        <Link href="/" className="sbs-brand">
          <span className="sbs-brand-mark" aria-hidden>
            CH
          </span>
          <span className="sbs-brand-text">
            <span className="sbs-brand-name">Compliance Hub</span>
            <span className="sbs-brand-tag">
              GRC · EU AI Act · NIS2 · ISO 42001
            </span>
          </span>
        </Link>
        <nav className="sbs-header-nav" aria-label="Hauptnavigation">
          {nav.map((item) => (
            <Link key={item.href} href={item.href}>
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
