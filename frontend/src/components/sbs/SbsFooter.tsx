import Link from "next/link";
import React from "react";

import { contactPageHref } from "@/lib/publicContact";

type SbsFooterProps = {
  publicSite?: boolean;
};

export function SbsFooter({ publicSite = false }: SbsFooterProps) {
  const y = new Date().getFullYear();
  if (publicSite) {
    return (
      <footer className="sbs-premium-footer mt-auto border-t border-white/10 bg-[#07111f] py-12 text-white">
        <div className="mx-auto grid min-w-0 max-w-[90rem] gap-10 px-4 md:grid-cols-[1.4fr_1fr_1fr] md:px-8">
          <div className="max-w-md">
            <p className="text-base font-semibold tracking-[-0.02em]">Compliance Hub</p>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              Enterprise AI Governance für nachvollziehbare Controls, Evidence und
              verantwortliche Entscheidungen.
            </p>
          </div>
          <nav aria-label="Unternehmen">
            <h2 className="text-[0.65rem] font-bold uppercase tracking-wider text-slate-500">
              Unternehmen
            </h2>
            <ul className="mt-3 space-y-2 text-sm">
              <li><Link href="/" prefetch={false} className="text-slate-300 hover:text-white">Start</Link></li>
              <li><Link href="/trust-center" prefetch={false} className="text-slate-300 hover:text-white">Trust Center</Link></li>
              <li><Link href="/kontakt" prefetch={false} className="text-slate-300 hover:text-white">Kontakt</Link></li>
            </ul>
          </nav>
          <nav aria-label="Rechtliches">
            <h2 className="text-[0.65rem] font-bold uppercase tracking-wider text-slate-500">
              Rechtliches
            </h2>
            <ul className="mt-3 space-y-2 text-sm">
              <li><Link href="/impressum" prefetch={false} className="text-slate-300 hover:text-white">Impressum</Link></li>
              <li><Link href="/datenschutz" prefetch={false} className="text-slate-300 hover:text-white">Datenschutz</Link></li>
            </ul>
          </nav>
          <p className="border-t border-white/10 pt-6 text-xs text-slate-500 md:col-span-3">
            © {y} Compliance Hub · Öffentliche Produktinformation · Keine Rechtsberatung
          </p>
        </div>
      </footer>
    );
  }

  return (
    <footer className="sbs-premium-footer mt-auto border-t border-slate-200/70 bg-[#07111f] py-12 text-white">
      <div className="mx-auto min-w-0 max-w-[90rem] px-4 md:px-8">
        <div className="grid grid-cols-2 gap-8 sm:grid-cols-3 lg:grid-cols-5">
          <div>
            <h3 className="text-[0.65rem] font-bold uppercase tracking-wider text-slate-500">
              Plattform
            </h3>
            <ul className="mt-3 space-y-2 text-xs">
              <li>
                <Link href="/board/kpis" className="font-medium text-slate-600 hover:text-slate-900">
                  Board KPIs
                </Link>
              </li>
              <li>
                <Link
                  href="/tenant/compliance-overview"
                  className="font-medium text-slate-600 hover:text-slate-900"
                >
                  Workspace
                </Link>
              </li>
              <li>
                <Link
                  href="/ai-systems"
                  className="font-medium text-slate-600 hover:text-slate-900"
                >
                  AI Systems
                </Link>
              </li>
              <li>
                <Link
                  href="/incidents"
                  className="font-medium text-slate-600 hover:text-slate-900"
                >
                  Incidents
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-[0.65rem] font-bold uppercase tracking-wider text-slate-400">
              Reporting
            </h3>
            <ul className="mt-3 space-y-2 text-xs">
              <li>
                <Link
                  href="/board/executive-dashboard"
                  className="font-medium text-slate-600 hover:text-slate-900"
                >
                  Executive Dashboard
                </Link>
              </li>
              <li>
                <Link
                  href="/board/gap-analysis"
                  className="font-medium text-slate-600 hover:text-slate-900"
                >
                  Gap Analysis
                </Link>
              </li>
              <li>
                <Link
                  href="/board/compliance-calendar"
                  className="font-medium text-slate-600 hover:text-slate-900"
                >
                  Compliance Calendar
                </Link>
              </li>
              <li>
                <Link
                  href="/board/datev-export"
                  className="font-medium text-slate-600 hover:text-slate-900"
                >
                  DATEV Export
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-[0.65rem] font-bold uppercase tracking-wider text-slate-400">
              Konto
            </h3>
            <ul className="mt-3 space-y-2 text-xs">
              <li>
                <Link
                  href="/auth/login"
                  className="font-medium text-slate-600 hover:text-slate-900"
                >
                  Anmelden
                </Link>
              </li>
              <li>
                <Link
                  href="/auth/register"
                  className="font-medium text-slate-600 hover:text-slate-900"
                >
                  Registrieren
                </Link>
              </li>
              <li>
                <Link
                  href="/settings"
                  className="font-medium text-slate-600 hover:text-slate-900"
                >
                  Einstellungen
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-[0.65rem] font-bold uppercase tracking-wider text-slate-400">
              Unternehmen
            </h3>
            <ul className="mt-3 space-y-2 text-xs">
              <li>
                <Link href="/" className="font-medium text-slate-600 hover:text-slate-900">
                  Start
                </Link>
              </li>
              <li>
                <Link
                  href={contactPageHref({
                    quelle: "footer",
                    ctaId: "footer-kontakt",
                    ctaLabel: "Kontakt",
                  })}
                  className="font-medium text-slate-600 hover:text-slate-900"
                >
                  Kontakt
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-[0.65rem] font-bold uppercase tracking-wider text-slate-400">
              Rechtliches
            </h3>
            <ul className="mt-3 space-y-2 text-xs">
              <li>
                <Link href="/impressum" className="font-medium text-slate-600 hover:text-slate-900">
                  Impressum
                </Link>
              </li>
              <li>
                <Link href="/datenschutz" className="font-medium text-slate-600 hover:text-slate-900">
                  Datenschutz
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-8 border-t border-slate-200/60 pt-6 text-xs text-slate-500">
          © {y} Compliance Hub · Enterprise GRC für den DACH-Markt
        </div>
      </div>
    </footer>
  );
}
