"use client";

import { usePathname } from "next/navigation";
import React from "react";

import { DEMO_GUIDE_STEPS, demoStepIndexForPath } from "@/lib/demoGuideSteps";

export function DemoContextualHint({ enabled }: { enabled: boolean }) {
  const pathname = usePathname() || "";
  if (!enabled) {
    return null;
  }
  const idx = demoStepIndexForPath(pathname);
  if (idx === null) {
    return null;
  }
  const step = DEMO_GUIDE_STEPS[idx];
  return (
    <div className="mb-4 rounded-lg border border-sky-200/80 bg-sky-50/90 px-3 py-2 text-sm text-sky-950">
      <span className="font-semibold text-sky-900">Demo-Hinweis · Schritt {idx + 1} von </span>
      <span className="font-semibold text-sky-900">{DEMO_GUIDE_STEPS.length}</span>
      <span className="text-sky-900/90"> — {step.hint}</span>
    </div>
  );
}
