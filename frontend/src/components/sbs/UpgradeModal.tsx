"use client";

import React, { useEffect, useRef } from "react";

import { CH_BTN_PRIMARY, CH_BTN_SECONDARY } from "@/lib/boardLayout";

/**
 * Simple modal shown when a user clicks on a feature-gated nav item.
 * Prompts the user to upgrade to a higher plan.
 */
export function UpgradeModal({
  planLabel,
  onClose,
}: {
  planLabel: string;
  onClose: () => void;
}) {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      ref={overlayRef}
      role="dialog"
      aria-modal="true"
      aria-label="Upgrade erforderlich"
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 p-4"
      onClick={(e) => {
        if (e.target === overlayRef.current) onClose();
      }}
    >
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-slate-900">
          Upgrade auf {planLabel}
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-600">
          Diese Funktion ist im aktuellen Plan nicht verfügbar.
          Upgraden Sie auf <strong>{planLabel}</strong>, um Zugriff
          zu erhalten.
        </p>
        <div className="mt-5 flex gap-3">
          <a
            href="/settings"
            className={CH_BTN_PRIMARY}
          >
            Plan upgraden
          </a>
          <button type="button" onClick={onClose} className={CH_BTN_SECONDARY}>
            Schließen
          </button>
        </div>
      </div>
    </div>
  );
}
