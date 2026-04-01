import type { Metadata } from "next";
import { Suspense } from "react";

import { ContactLeadForm } from "@/components/contact/ContactLeadForm";
import { CH_PAGE_SUB, CH_PAGE_TITLE, CH_SHELL } from "@/lib/boardLayout";

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
      <Suspense fallback={<FormFallback />}>
        <ContactLeadForm />
      </Suspense>
    </div>
  );
}
