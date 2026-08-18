import type { Metadata } from "next";
import Link from "next/link";
import React from "react";

export const metadata: Metadata = {
  title: "Anmeldung · Compliance Hub",
};

/**
 * Dedicated auth layout: centres the form card, shows a minimal
 * brand link so the user can navigate back to the public landing.
 * The root layout still provides SbsHeader / SbsFooter around this.
 */
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-md flex-col items-center justify-center">
      <div className="mb-6 text-center">
        <Link
          href="/"
          className="text-sm font-semibold text-slate-600 transition hover:text-cyan-700"
        >
          ← Zurück zur Startseite
        </Link>
      </div>
      <div className="w-full">{children}</div>
    </div>
  );
}
