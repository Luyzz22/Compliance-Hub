import type { Metadata } from "next";
import React from "react";

import { LegalReleaseGate } from "@/components/legal/LegalReleaseGate";
import { CH_CARD, CH_SHELL } from "@/lib/boardLayout";
import { getLegalConfig } from "@/lib/legalConfig";

export const metadata: Metadata = {
  title: "Impressum · Compliance Hub",
};

export default function ImpressumPage() {
  const legal = getLegalConfig();
  return (
    <div className={CH_SHELL}>
      <header className="mb-8 border-b border-slate-200/80 pb-8">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-700">
          Rechtliches
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
          Impressum
        </h1>
        <p className="mt-2 max-w-2xl text-base leading-relaxed text-slate-600">
          Anbieterkennzeichnung gemäß § 5 DDG.
        </p>
      </header>
      {!legal ? (
        <LegalReleaseGate />
      ) : (
        <div className={`${CH_CARD} space-y-6 text-sm leading-6 text-slate-700`}>
          <section>
            <h2 className="font-semibold text-slate-950">Diensteanbieter</h2>
            <address className="mt-2 not-italic">
              {legal.entityName}<br />
              {legal.street}<br />
              {legal.postalCode} {legal.city}<br />
              {legal.country}
            </address>
          </section>
          <section>
            <h2 className="font-semibold text-slate-950">Vertretungsberechtigt</h2>
            <p className="mt-2">{legal.representative}</p>
          </section>
          <section>
            <h2 className="font-semibold text-slate-950">Kontakt</h2>
            <p className="mt-2">
              E-Mail: <a href={`mailto:${legal.email}`}>{legal.email}</a>
              {legal.phone ? <><br />Telefon: {legal.phone}</> : null}
            </p>
          </section>
          <section>
            <h2 className="font-semibold text-slate-950">Registerangaben</h2>
            <p className="mt-2">
              Registergericht: {legal.registerCourt}<br />
              Registernummer: {legal.registerNumber}<br />
              Umsatzsteuer-Identifikationsnummer: {legal.vatId}
            </p>
          </section>
        </div>
      )}
    </div>
  );
}
