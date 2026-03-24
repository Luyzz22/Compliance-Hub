"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React from "react";

const items = [
  { href: "/tenant/compliance-overview", label: "Mandant & Einstellungen" },
  { href: "/tenant/eu-ai-act", label: "EU AI Act" },
  { href: "/tenant/ai-systems", label: "AI Systems" },
  { href: "/tenant/policies", label: "Policies & Rules" },
  { href: "/tenant/audit-log", label: "Audit Log" },
  { href: "/tenant/blueprints", label: "Blueprints & Settings" },
];

export function TenantNav() {
  const pathname = usePathname();
  return (
    <nav
      className="px-3 py-4 space-y-1"
      style={{ fontSize: "0.875rem" }}
      aria-label="Tenant-Navigation"
    >
      <div
        className="px-2 pb-2 text-xs font-semibold uppercase tracking-wide"
        style={{ color: "#64748b" }}
      >
        Overview
      </div>
      {items.map((item) => {
        const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              borderRadius: "0.5rem",
              padding: "0.4rem 0.5rem",
              textDecoration: "none",
              color: active ? "#fff" : "#94a3b8",
              background: active ? "rgba(0, 102, 179, 0.35)" : "transparent",
            }}
          >
            <span
              className="h-1.5 w-1.5 shrink-0 rounded-full"
              style={{
                background: active ? "#fbbf24" : "#475569",
              }}
            />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
