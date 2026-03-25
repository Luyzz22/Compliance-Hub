"use client";

import Link from "next/link";
import { useEffect } from "react";

import { CH_BTN_SECONDARY, CH_SHELL } from "@/lib/boardLayout";

export function ServiceUnavailableError({
  error,
  reset,
  title = "Service vorübergehend nicht verfügbar",
}: {
  error: Error & { digest?: string };
  reset: () => void;
  title?: string;
}) {
  useEffect(() => {
    // Sichtbar für Betrieb / Support (kein sensibler Inhalt)
    console.error("[ComplianceHub]", error.message, error.digest ?? "");
  }, [error]);

  return (
    <div className={CH_SHELL}>
      <div
        className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-slate-900"
        role="alert"
      >
        <h1 className="text-lg font-semibold">{title}</h1>
        <p className="mt-2 text-sm text-slate-700">
          Diese Ansicht konnte nicht geladen werden. Bitte versuchen Sie es später erneut. Bei
          anhaltenden Problemen wenden Sie sich an den Support oder prüfen Sie die
          Einstellungen.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <button type="button" className={CH_BTN_SECONDARY} onClick={() => reset()}>
            Erneut versuchen
          </button>
          <Link href="/settings" className={`${CH_BTN_SECONDARY} inline-flex items-center`}>
            Zu den Einstellungen
          </Link>
        </div>
      </div>
    </div>
  );
}
