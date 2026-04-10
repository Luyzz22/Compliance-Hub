"use client";

import Link from "next/link";
import React, { useSyncExternalStore } from "react";

const COOKIE_CONSENT_KEY = "ch_cookie_consent";

function subscribeStorage(cb: () => void) {
  window.addEventListener("storage", cb);
  return () => window.removeEventListener("storage", cb);
}

function getConsentSnapshot(): boolean {
  if (typeof window === "undefined") return true; // SSR: hide banner
  return localStorage.getItem(COOKIE_CONSENT_KEY) !== null;
}

function getConsentServerSnapshot(): boolean {
  return true; // server: assume accepted → no banner
}

/**
 * Simplified cookie consent banner.
 * Since the platform does not use third-party cookies, a simple
 * informational banner is sufficient under German/EU law.
 */
export function CookieBanner() {
  const hasConsented = useSyncExternalStore(
    subscribeStorage,
    getConsentSnapshot,
    getConsentServerSnapshot,
  );

  function accept() {
    localStorage.setItem(COOKIE_CONSENT_KEY, "accepted");
    // Force re-render by dispatching storage event manually
    window.dispatchEvent(new StorageEvent("storage"));
  }

  if (hasConsented) return null;

  return (
    <div
      role="dialog"
      aria-label="Cookie-Hinweis"
      className="fixed bottom-0 inset-x-0 z-[90] border-t border-slate-200/90 bg-white p-4 shadow-lg md:flex md:items-center md:justify-between md:gap-4 md:px-6"
    >
      <p className="text-xs leading-relaxed text-slate-600 md:text-sm">
        Diese Website verwendet ausschließlich technisch notwendige Cookies.
        Weitere Informationen finden Sie in unserer{" "}
        <Link
          href="/datenschutz"
          className="font-medium text-cyan-700 underline underline-offset-2"
        >
          Datenschutzerklärung
        </Link>
        .
      </p>
      <button
        type="button"
        onClick={accept}
        className="mt-3 inline-flex shrink-0 items-center justify-center rounded-full bg-cyan-700 px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-cyan-800 md:mt-0"
      >
        Verstanden
      </button>
    </div>
  );
}
