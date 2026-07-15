import type { Metadata } from "next";
import { Suspense } from "react";

import { ContactLeadForm } from "@/components/contact/ContactLeadForm";
import { CH_PAGE_SUB, CH_PAGE_TITLE, CH_SHELL } from "@/lib/boardLayout";
import { PUBLIC_CONTACT_EMAIL, PUBLIC_CONTACT_MAILTO } from "@/lib/publicContact";
import { isPublicSiteRelease } from "@/lib/releaseProfile";

export const metadata: Metadata = {
  title: "Kontakt & Demo · Compliance Hub",
  description:
    "Unverbindliche Demo- oder Beratungsanfrage zu AI Act Readiness, Governance & Evidence und Enterprise Connectors. Keine Rechtsberatung.",
};

function FormFallback() {
  return (
    <p className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600 shadow-sm">
      Formular wird geladen …
    </p>
  );
}

export default function KontaktPage() {
  const publicSite = isPublicSiteRelease();

  return (
    <div className={CH_SHELL}>
      <div className="max-w-2xl">
        <h1 className={CH_PAGE_TITLE}>Kontakt &amp; Demo anfragen</h1>
        <p className={CH_PAGE_SUB}>
          Beschreiben Sie kurz Ihr Anliegen. Wir melden uns für ein unverbindliches Gespräch zu
          Paketen (AI Act Readiness, Governance &amp; Evidence, Enterprise Connectors) und
          nächsten Schritten.
        </p>
      </div>
      {publicSite ? (
        <section className="max-w-2xl rounded-[1.75rem] border border-slate-200/80 bg-white p-6 shadow-xl shadow-slate-200/40 sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-700">
            Direkter Kontakt
          </p>
          <h2 className="mt-3 text-xl font-semibold tracking-tight text-slate-950">
            Ihr Anliegen bleibt unter Ihrer Kontrolle.
          </h2>
          <p className="mt-3 text-sm leading-7 text-slate-600">
            Der öffentliche Release speichert keine Formulardaten. Schreiben Sie uns direkt;
            Sie entscheiden selbst, welche Informationen Sie übermitteln.
          </p>
          <a
            href={PUBLIC_CONTACT_MAILTO}
            className="mt-6 inline-flex min-h-12 items-center justify-center rounded-full bg-[#07111f] px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-slate-950/15 transition hover:-translate-y-0.5 hover:bg-slate-800"
          >
            {PUBLIC_CONTACT_EMAIL}
          </a>
          <p className="mt-5 text-xs leading-5 text-slate-500">
            Bitte senden Sie keine besonderen Kategorien personenbezogener Daten oder
            vertrauliche Mandantendaten per E-Mail.
          </p>
        </section>
      ) : (
        <Suspense fallback={<FormFallback />}>
          <ContactLeadForm />
        </Suspense>
      )}
    </div>
  );
}
