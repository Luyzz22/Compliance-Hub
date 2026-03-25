"use client";

import React from "react";

import { useWorkspaceTenantMeta } from "@/hooks/useWorkspaceTenantMeta";

/**
 * Kompaktes Badge in der Mandanten-Shell: Demo vs. Playground vs. Schreibschutz.
 */
export function DemoWorkspaceBadge({ tenantId }: { tenantId: string }) {
  const { loading, isDemoTenant, isPlaygroundTenant, mutationBlocked } = useWorkspaceTenantMeta(tenantId);

  if (loading || !isDemoTenant) {
    return null;
  }

  const label = isPlaygroundTenant ? "Playground" : "Demo";
  const title = mutationBlocked
    ? "Schreibgeschützter Demo-Mandant: keine persistierenden Änderungen über die API."
    : "Sandbox-Mandant (demo_playground): begrenzte Schreiboperationen möglich.";

  return (
    <span
      className="inline-flex max-w-full items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-2.5 py-0.5 text-[0.65rem] font-bold uppercase tracking-wide text-amber-950"
      title={title}
    >
      <span aria-hidden>●</span>
      {label}
      {mutationBlocked ? " · read-only" : null}
    </span>
  );
}
