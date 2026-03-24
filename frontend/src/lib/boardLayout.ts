/** Seiten-Root innerhalb des globalen `<main>` (kein verschachteltes `<main>`). */
export const BOARD_PAGE_ROOT_CLASS = "min-w-0";

/** Einheitliche Karten (Apple-/AI-SaaS-inspiriert). */
export const CH_CARD =
  "rounded-2xl border border-slate-200/90 bg-white p-5 shadow-md shadow-slate-200/50";

export const CH_CARD_MUTED =
  "rounded-2xl border border-slate-200/60 bg-slate-50/80 p-5 shadow-sm";

export const CH_PAGE_TITLE =
  "text-3xl font-semibold tracking-tight text-slate-900 sm:text-[2rem] sm:leading-tight";

export const CH_PAGE_SUB =
  "mt-2 max-w-2xl text-base leading-relaxed text-slate-600";

export const CH_SECTION_LABEL =
  "text-xs font-semibold uppercase tracking-[0.12em] text-slate-500";

export const CH_BTN_PRIMARY =
  "inline-flex items-center justify-center rounded-xl bg-cyan-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-cyan-700";

export const CH_BTN_SECONDARY =
  "inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 shadow-sm transition hover:border-slate-300 hover:bg-slate-50";

export const CH_BTN_GHOST =
  "inline-flex items-center justify-center rounded-xl border border-transparent px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100";

/** Status-Badge für KPI-Ratios 0–1 (Enterprise-Dashboard). */
export function chKpiStatusFromRatio(ratio: number): {
  label: string;
  chipClass: string;
} {
  if (ratio < 0.4) {
    return {
      label: "Kritisch",
      chipClass: "bg-red-100 text-red-900 ring-red-200/70",
    };
  }
  if (ratio < 0.75) {
    return {
      label: "Beobachten",
      chipClass: "bg-amber-100 text-amber-950 ring-amber-200/70",
    };
  }
  return {
    label: "Im Plan",
    chipClass: "bg-emerald-100 text-emerald-900 ring-emerald-200/70",
  };
}
