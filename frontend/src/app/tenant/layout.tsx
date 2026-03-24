import React from "react";

import { TenantNav } from "@/components/sbs/TenantNav";

export default function TenantLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="sbs-tenant-shell">
      <aside className="sbs-tenant-sidebar">
        <div
          style={{
            padding: "1.25rem",
            borderBottom: "1px solid rgba(148,163,184,0.15)",
          }}
        >
          <div
            style={{
              fontSize: "0.65rem",
              fontWeight: 700,
              letterSpacing: "0.12em",
              color: "#94a3b8",
            }}
          >
            COMPLIANCE HUB
          </div>
          <div
            style={{ marginTop: "0.35rem", fontSize: "0.85rem", color: "#e2e8f0" }}
          >
            Tenant:{" "}
            <strong style={{ fontWeight: 600 }}>tenant-overview-001</strong>
          </div>
        </div>
        <TenantNav />
      </aside>
      <div className="sbs-tenant-main">{children}</div>
    </div>
  );
}
