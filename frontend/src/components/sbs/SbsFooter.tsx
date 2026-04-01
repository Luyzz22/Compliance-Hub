import Link from "next/link";
import React from "react";

import { PUBLIC_CONTACT_MAILTO } from "@/lib/publicContact";

export function SbsFooter() {
  const y = new Date().getFullYear();
  return (
    <footer className="mt-auto border-t border-slate-200/90 bg-white py-10">
      <div className="mx-auto flex min-w-0 max-w-7xl flex-col gap-4 px-4 text-xs text-slate-500 md:flex-row md:items-center md:justify-between md:px-6">
        <div className="leading-relaxed">
          © {y} Compliance Hub · Enterprise GRC für den DACH-Markt
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-2">
          <Link href="/" className="font-medium text-slate-600 hover:text-slate-900">
            Start
          </Link>
          <Link href="/board/kpis" className="font-medium text-slate-600 hover:text-slate-900">
            Board KPIs
          </Link>
          <Link
            href="/tenant/compliance-overview"
            className="font-medium text-slate-600 hover:text-slate-900"
          >
            Tenant
          </Link>
          <Link href="/board/suppliers" className="font-medium text-slate-600 hover:text-slate-900">
            Supplier
          </Link>
          <a
            href={PUBLIC_CONTACT_MAILTO}
            className="font-medium text-slate-600 hover:text-slate-900"
          >
            Kontakt
          </a>
        </div>
      </div>
    </footer>
  );
}
