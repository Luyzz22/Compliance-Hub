"use client";

/**
 * Hydration-safe hook that checks feature gates against the billing API.
 *
 * Instead of a static URL list, this hook calls `/billing/feature-check`
 * for each gated nav path.  On the server (and during the first client
 * render) every gated path is treated as locked (fail-closed).  After
 * hydration an effect fires, queries the API, and unlocks paths the
 * tenant's plan already covers.
 */

import { useEffect, useState } from "react";

/* ── Feature-gate mapping ──────────────────────────────────────────── */

/** Maps nav paths to their feature key + human-readable plan label. */
export const NAV_FEATURE_GATES: Readonly<
  Record<string, { feature: string; requiredPlan: string }>
> = {
  "/board/datev-export": {
    feature: "datev_export",
    requiredPlan: "Professional",
  },
  "/board/xrechnung-export": {
    feature: "xrechnung",
    requiredPlan: "Enterprise",
  },
  "/board/gap-analysis": {
    feature: "rag_gap_analysis",
    requiredPlan: "Professional",
  },
};

/* ── Internals ─────────────────────────────────────────────────────── */

const API_BASE_URL =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_API_BASE_URL ||
      process.env.COMPLIANCEHUB_API_BASE_URL ||
      "http://localhost:8000"
    : "";
const API_KEY =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_API_KEY ||
      process.env.COMPLIANCEHUB_API_KEY ||
      "tenant-overview-key"
    : "";
const TENANT_ID =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_TENANT_ID ||
      process.env.COMPLIANCEHUB_TENANT_ID ||
      "tenant-overview-001"
    : "";

/** All paths that *could* be gated — used as fail-closed default. */
const ALL_GATED = new Set(Object.keys(NAV_FEATURE_GATES));

/* ── Public API ────────────────────────────────────────────────────── */

export interface FeatureGateResult {
  /** Returns `true` when the path is gated (user lacks plan access). */
  isGated: (href: string) => boolean;
  /** Human-readable plan label for the upgrade prompt. */
  requiredPlanLabel: (href: string) => string;
}

/**
 * Hook that resolves feature gates via the billing API.
 *
 * Hydration-safe: the initial render always treats gated paths as locked
 * so the server HTML and first client paint match (no flash).  A
 * `useEffect` then queries `/billing/feature-check` per feature and
 * unlocks paths whose features the current plan already covers.
 */
export function useFeatureGate(): FeatureGateResult {
  const [gatedPaths, setGatedPaths] = useState<ReadonlySet<string>>(ALL_GATED);

  useEffect(() => {
    // Skip when running server-side (should never happen with "use client",
    // but guard defensively).
    if (typeof window === "undefined") return;

    let cancelled = false;
    const entries = Object.entries(NAV_FEATURE_GATES);
    if (entries.length === 0) return;

    const headers: Record<string, string> = {
      "x-api-key": API_KEY,
      "x-tenant-id": TENANT_ID,
    };
    const opaRole = process.env.NEXT_PUBLIC_OPA_USER_ROLE?.trim();
    if (opaRole) headers["x-opa-user-role"] = opaRole;

    Promise.allSettled(
      entries.map(async ([, gate]) => {
        const res = await fetch(
          `${API_BASE_URL}/api/v1/enterprise/billing/feature-check?feature=${encodeURIComponent(gate.feature)}`,
          { headers, cache: "no-store" },
        );
        return res.ok; // 200 → accessible, 402 → gated
      }),
    ).then((results) => {
      if (cancelled) return;
      const stillGated = new Set<string>();
      results.forEach((r, i) => {
        const path = entries[i][0];
        if (r.status === "fulfilled" && r.value) {
          // Feature is accessible — do NOT gate it
        } else {
          // 402 / network error → fail-closed: keep gated
          stillGated.add(path);
        }
      });
      setGatedPaths(stillGated);
    });

    return () => {
      cancelled = true;
    };
  }, []);

  return {
    isGated: (href: string) => gatedPaths.has(href),
    requiredPlanLabel: (href: string) =>
      NAV_FEATURE_GATES[href]?.requiredPlan ?? "Professional",
  };
}
