"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import React, { useCallback, useMemo, useState } from "react";

import { fetchTenantAISystems } from "@/lib/api";
import { DEMO_GUIDE_STEPS, demoStepIndexForPath } from "@/lib/demoGuideSteps";

function riskIsHigh(raw: string | undefined): boolean {
  if (!raw) {
    return false;
  }
  return raw.toLowerCase().includes("high") || raw.toLowerCase() === "high";
}

export function DemoGuide({ tenantId, enabled }: { tenantId: string; enabled: boolean }) {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const pathname = usePathname() || "";
  const currentIdx = useMemo(() => demoStepIndexForPath(pathname), [pathname]);

  const goStep = useCallback(
    async (path: string, resolveHr?: boolean) => {
      if (!resolveHr) {
        router.push(path);
        setOpen(false);
        return;
      }
      try {
        const systems = await fetchTenantAISystems(tenantId);
        const hr = systems.find((s) => riskIsHigh(s.risk_level ?? s.risklevel));
        const pick = hr ?? systems[0];
        if (pick?.id) {
          router.push(`/tenant/ai-systems/${encodeURIComponent(pick.id)}`);
        } else {
          router.push("/tenant/ai-systems");
        }
      } catch {
        router.push("/tenant/ai-systems");
      }
      setOpen(false);
    },
    [router, tenantId],
  );

  const goNext = useCallback(async () => {
    if (currentIdx === null) {
      await goStep(DEMO_GUIDE_STEPS[0].path, DEMO_GUIDE_STEPS[0].resolveHighRiskSystem);
      return;
    }
    const next = DEMO_GUIDE_STEPS[(currentIdx + 1) % DEMO_GUIDE_STEPS.length];
    await goStep(next.path, next.resolveHighRiskSystem);
  }, [currentIdx, goStep]);

  if (!enabled) {
    return null;
  }

  return (
    <>
      <div className="pointer-events-none fixed bottom-6 right-4 z-40 flex flex-col items-end gap-2 md:right-6">
        <button
          type="button"
          className="pointer-events-auto rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800 shadow-md hover:bg-slate-50"
          onClick={() => setOpen(true)}
        >
          Demo-Guide
        </button>
        {currentIdx !== null ? (
          <button
            type="button"
            className="pointer-events-auto rounded-full border border-indigo-200 bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-md hover:bg-indigo-700"
            onClick={() => void goNext()}
          >
            Nächster Demo-Schritt
          </button>
        ) : null}
      </div>

      {open ? (
        <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/40" role="dialog">
          <div className="flex h-full w-full max-w-md flex-col bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
              <h2 className="text-lg font-semibold text-slate-900">Geführte Demo</h2>
              <button
                type="button"
                className="rounded px-2 py-1 text-sm text-slate-600 hover:bg-slate-100"
                onClick={() => setOpen(false)}
              >
                Schließen
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-4 py-3">
              <ol className="space-y-4">
                {DEMO_GUIDE_STEPS.map((step, i) => (
                  <li
                    key={step.id}
                    className={`rounded-lg border px-3 py-2 ${
                      currentIdx === i ? "border-indigo-300 bg-indigo-50/80" : "border-slate-200"
                    }`}
                  >
                    <div className="text-xs font-bold uppercase tracking-wide text-slate-500">
                      Schritt {i + 1}
                    </div>
                    <div className="font-medium text-slate-900">{step.title}</div>
                    <p className="mt-1 text-sm text-slate-600">{step.hint}</p>
                    <button
                      type="button"
                      className="mt-2 text-sm font-semibold text-indigo-700 hover:text-indigo-900"
                      onClick={() => void goStep(step.path, step.resolveHighRiskSystem)}
                    >
                      Diesen Schritt öffnen →
                    </button>
                  </li>
                ))}
              </ol>
              <p className="mt-4 text-xs text-slate-500">
                Kurzlink mit Session-Cookie:{" "}
                <Link href="/?demo=1" className="text-indigo-700 underline">
                  ?demo=1
                </Link>{" "}
                (optional{" "}
                <code className="rounded bg-slate-100 px-1">NEXT_PUBLIC_DEMO_WORKSPACE_TENANT_ID</code>
                ).
              </p>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
