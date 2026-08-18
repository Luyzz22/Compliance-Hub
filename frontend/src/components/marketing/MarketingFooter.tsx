import Link from "next/link";
import React from "react";

import { FOOTER_COLUMNS, MARKETING_ROUTES } from "@/lib/marketing/navigation";
import { PUBLIC_CONTACT_EMAIL, PUBLIC_CONTACT_MAILTO } from "@/lib/publicContact";

export function MarketingFooter() {
  const year = new Date().getFullYear();

  return (
    <footer className="mk-dark mt-auto bg-[var(--mk-navy-950)]">
      <div className="mk-container py-12 lg:py-14">
        <div className="grid gap-10 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,3fr)]">
          <div className="max-w-sm">
            <p className="text-[0.9375rem] font-semibold tracking-[-0.02em] text-white">
              Compliance Hub
            </p>
            <p className="mt-3 text-[0.8125rem] leading-relaxed text-[var(--mk-fg-muted)]">
              Der Governance-Layer für AI, Security und Compliance im DACH-Mittelstand.
              Ein Kontrollmodell, mehrere Regelwerke, nachvollziehbare Evidenz.
            </p>
            <dl className="mt-5 space-y-1.5 text-[0.8125rem]">
              <div className="flex gap-2">
                <dt className="text-[var(--mk-fg-faint)]">Kontakt</dt>
                <dd>
                  <a
                    href={PUBLIC_CONTACT_MAILTO}
                    className="text-[var(--mk-fg-soft)] no-underline hover:text-white"
                  >
                    {PUBLIC_CONTACT_EMAIL}
                  </a>
                </dd>
              </div>
              <div className="flex gap-2">
                <dt className="text-[var(--mk-fg-faint)]">LinkedIn</dt>
                <dd>
                  <a
                    href="https://www.linkedin.com/company/complywithai"
                    rel="noopener noreferrer nofollow"
                    target="_blank"
                    className="text-[var(--mk-fg-soft)] no-underline hover:text-white"
                  >
                    /company/complywithai
                  </a>
                </dd>
              </div>
            </dl>
          </div>

          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-5">
            {FOOTER_COLUMNS.map((column) => (
              <nav key={column.title} aria-label={column.title}>
                <h2 className="text-[0.6875rem] font-bold uppercase tracking-[0.12em] text-[var(--mk-fg-faint)]">
                  {column.title}
                </h2>
                <ul className="mt-3.5 space-y-2.5">
                  {column.items.map((item) => (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        prefetch={false}
                        className="text-[0.8125rem] text-[var(--mk-fg-soft)] no-underline transition-colors hover:text-white"
                      >
                        {item.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </nav>
            ))}
          </div>
        </div>

        <div className="mt-10 flex flex-col gap-3 border-t border-white/10 pt-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-[0.75rem] text-[var(--mk-fg-faint)]">
            © {year} Compliance Hub · Enterprise GRC für den DACH-Markt
          </p>
          <ul className="flex flex-wrap gap-x-5 gap-y-2 text-[0.75rem]">
            <li>
              <Link
                href={MARKETING_ROUTES.imprint}
                prefetch={false}
                className="text-[var(--mk-fg-faint)] no-underline hover:text-white"
              >
                Impressum
              </Link>
            </li>
            <li>
              <Link
                href={MARKETING_ROUTES.privacy}
                prefetch={false}
                className="text-[var(--mk-fg-faint)] no-underline hover:text-white"
              >
                Datenschutz
              </Link>
            </li>
            <li>
              <Link
                href={MARKETING_ROUTES.contact}
                prefetch={false}
                className="text-[var(--mk-fg-faint)] no-underline hover:text-white"
              >
                Kontakt
              </Link>
            </li>
          </ul>
        </div>

        <p className="mt-4 max-w-3xl text-[0.6875rem] leading-relaxed text-[var(--mk-fg-faint)]">
          Compliance Hub unterstützt Ihre Organisation bei der strukturierten Umsetzung
          regulatorischer Anforderungen und schafft nachvollziehbare Evidenzen und
          Governance-Workflows. Die Plattform erbringt keine Rechtsberatung und sagt keine
          Konformität zu; Bewertung und Freigabe bleiben bei den verantwortlichen Personen
          Ihrer Organisation.
        </p>
      </div>
    </footer>
  );
}
