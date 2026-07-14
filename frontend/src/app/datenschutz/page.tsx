import type { Metadata } from "next";
import React from "react";

import { LegalReleaseGate } from "@/components/legal/LegalReleaseGate";
import { CH_CARD, CH_SHELL } from "@/lib/boardLayout";
import { getLegalConfig } from "@/lib/legalConfig";

export const metadata: Metadata = {
  title: "Datenschutzerklärung · Compliance Hub",
};

export default function DatenschutzPage() {
  const legal = getLegalConfig();
  return (
    <div className={CH_SHELL}>
      <header className="mb-8 border-b border-slate-200/80 pb-8">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-700">
          Rechtliches
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
          Datenschutzerklärung
        </h1>
        <p className="mt-2 max-w-2xl text-base leading-relaxed text-slate-600">
          Informationen gemäß DSGVO Art. 13 / Art. 14.
        </p>
      </header>
      {!legal ? (
        <LegalReleaseGate />
      ) : (
        <article className={`${CH_CARD} space-y-8 text-sm leading-6 text-slate-700`}>
          <p className="text-xs text-slate-500">
            Version {legal.privacyNoticeVersion} · geprüft am {legal.privacyReviewedAt}
          </p>
          <section>
            <h2 className="text-lg font-semibold text-slate-950">1. Verantwortlicher</h2>
            <address className="mt-2 not-italic">
              {legal.entityName}, {legal.street}, {legal.postalCode} {legal.city},{" "}
              {legal.country}<br />
              Datenschutzkontakt: <a href={`mailto:${legal.privacyEmail}`}>{legal.privacyEmail}</a>
              {legal.dpoContact ? <><br />Datenschutzbeauftragter: {legal.dpoContact}</> : null}
            </address>
          </section>
          <section>
            <h2 className="text-lg font-semibold text-slate-950">2. Website und Protokolldaten</h2>
            <p className="mt-2">
              Beim Abruf werden technisch erforderliche Verbindungsdaten verarbeitet, um die
              Website sicher und verfügbar bereitzustellen. Rechtsgrundlage ist Art. 6 Abs. 1
              lit. f DSGVO. Sicherheitsprotokolle werden regulär nach {legal.logRetentionDays}{" "}
              Tagen gelöscht, sofern kein konkreter Sicherheitsvorfall eine längere Aufbewahrung
              erfordert.
            </p>
          </section>
          <section>
            <h2 className="text-lg font-semibold text-slate-950">3. Kontakt und Demo-Anfragen</h2>
            <p className="mt-2">
              Wir verarbeiten Ihre Angaben zur Bearbeitung der Anfrage und zur Vorbereitung
              eines Vertragsverhältnisses nach Art. 6 Abs. 1 lit. b DSGVO; bei allgemeinen
              geschäftlichen Anfragen zusätzlich auf Grundlage von Art. 6 Abs. 1 lit. f DSGVO.
              Nicht weiter benötigte Lead-Daten werden regulär nach {legal.leadRetentionDays}{" "}
              Tagen gelöscht, soweit keine gesetzlichen Pflichten entgegenstehen.
            </p>
          </section>
          <section>
            <h2 className="text-lg font-semibold text-slate-950">4. Konten und Plattformnutzung</h2>
            <p className="mt-2">
              Konto-, Rollen-, Mandanten- und Nachweisdaten werden zur Vertragserfüllung,
              Zugriffskontrolle, Revisionsfähigkeit und IT-Sicherheit verarbeitet. Inhalte und
              Metadaten werden nach mandantenspezifischen Lösch- und Aufbewahrungsregeln
              behandelt. Gesetzliche Aufbewahrungspflichten bleiben unberührt.
            </p>
          </section>
          <section>
            <h2 className="text-lg font-semibold text-slate-950">5. KI-Funktionen</h2>
            <p className="mt-2">
              KI-Funktionen sind standardmäßig deaktiviert und werden mandantenspezifisch
              freigegeben. Erkannte personenbezogene Daten und Prompt-Injection-Muster werden
              vor einem Modellaufruf standardmäßig blockiert. Modellantworten sind Entwürfe;
              Aufrufe werden ausschließlich mit inhaltsfreien Betriebsmetadaten nachvollziehbar
              gemacht. Der freigegebene Prozess muss sicherstellen, dass keine ausschließlich
              automatisierte Entscheidung mit Rechtswirkung im Sinne von Art. 22 DSGVO erfolgt.
            </p>
          </section>
          <section>
            <h2 className="text-lg font-semibold text-slate-950">6. Empfänger und Übermittlungen</h2>
            <p className="mt-2">
              Empfänger erhalten Daten nur, soweit dies für Hosting, Betrieb, Support oder
              vertraglich aktivierte Integrationen erforderlich ist und eine Vereinbarung zur
              Auftragsverarbeitung oder andere Rechtsgrundlage besteht. Drittlandübermittlungen
              erfolgen nur unter den Voraussetzungen der Art. 44 ff. DSGVO. Die konkrete
              Subprozessorenliste und Datenregion ist im Trust Center der Vertragsinstanz
              dokumentiert.
            </p>
          </section>
          <section>
            <h2 className="text-lg font-semibold text-slate-950">7. Ihre Rechte</h2>
            <p className="mt-2">
              Sie haben insbesondere Rechte auf Auskunft, Berichtigung, Löschung,
              Einschränkung, Datenübertragbarkeit und Widerspruch sowie das Recht, eine
              Einwilligung mit Wirkung für die Zukunft zu widerrufen. Zudem können Sie sich
              bei einer Datenschutzaufsichtsbehörde beschweren.
            </p>
          </section>
        </article>
      )}
    </div>
  );
}
