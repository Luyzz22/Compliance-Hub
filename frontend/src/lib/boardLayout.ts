/** Seiten-Root innerhalb des globalen `<main>` (kein verschachteltes `<main>`). */
export const BOARD_PAGE_ROOT_CLASS = "min-w-0";

/** Vertikaler Rhythmus für Tenant-/Marketing-Seiten ohne überlappende Section-Abstände. */
export const CH_SHELL = "min-w-0 space-y-8 md:space-y-10";

/** Einheitliche Karten – helles Enterprise (dezenter Schatten). */
export const CH_CARD =
  "rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm shadow-slate-200/40";

export const CH_CARD_MUTED =
  "rounded-2xl border border-slate-200/60 bg-slate-50/90 p-5 shadow-sm";

export const CH_PAGE_TITLE =
  "text-3xl font-semibold tracking-tight text-slate-900 sm:text-[2rem] sm:leading-tight";

export const CH_PAGE_SUB =
  "mt-2 max-w-2xl text-base leading-relaxed text-slate-600";

export const CH_EYEBROW =
  "text-xs font-semibold uppercase tracking-[0.14em] text-cyan-700";

export const CH_SECTION_LABEL =
  "text-xs font-semibold uppercase tracking-[0.12em] text-slate-500";

/** Inline-Navigation unter dem Seitentitel */
export const CH_PAGE_NAV_LINK =
  "text-sm font-medium text-cyan-700 underline decoration-cyan-600/25 underline-offset-4 transition hover:text-cyan-900";

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
