"use client";

import type { HealthStatus } from "@/lib/internalHealth";

const STATUS_RING: Record<HealthStatus, string> = {
  up: "bg-emerald-50 text-emerald-900 ring-emerald-200/90",
  degraded: "bg-amber-50 text-amber-950 ring-amber-200/90",
  down: "bg-rose-50 text-rose-900 ring-rose-200/90",
};

const STATUS_DOT: Record<HealthStatus, string> = {
  up: "bg-emerald-500",
  degraded: "bg-amber-500",
  down: "bg-rose-600",
};

const STATUS_LABEL_DE: Record<HealthStatus, string> = {
  up: "OK",
  degraded: "Eingeschränkt",
  down: "Ausfall",
};

interface Props {
  status: HealthStatus;
  label: string;
}

/** Ampel-Pill für Betriebsstatus (App / DB / externer KI-Provider). */
export function HealthStatusPill({ status, label }: Props) {
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset ${STATUS_RING[status]}`}
    >
      <span
        className={`inline-block h-2.5 w-2.5 shrink-0 rounded-full ${STATUS_DOT[status]}`}
        aria-hidden
      />
      <span className="text-slate-700">{label}</span>
      <span className="tabular-nums text-slate-900">{STATUS_LABEL_DE[status]}</span>
    </span>
  );
}
