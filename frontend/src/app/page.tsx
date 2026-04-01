import Link from "next/link";
import React from "react";

import { TrackedContactLink } from "@/components/contact/TrackedContactLink";
import { HomeProductPreview } from "@/components/home/HomeProductPreview";
import { CH_BTN_PRIMARY, CH_BTN_SECONDARY } from "@/lib/boardLayout";
import { contactPageHref } from "@/lib/publicContact";

function SectionTitle({
  title,
  subtitle,
  id,
}: {
  title: string;
  subtitle: string;
  id?: string;
}) {
  return (
    <div className="mb-8 max-w-2xl">
      <h2
        id={id}
        className="text-lg font-semibold tracking-tight text-slate-900 sm:text-xl"
      >
        {title}
      </h2>
      <p className="mt-2 text-sm leading-relaxed text-slate-600 sm:text-[0.95rem]">
        {subtitle}
      </p>
    </div>
  );
}

export default function HomePage() {
  return (
    <div className="relative min-w-0">
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-10 opacity-70"
        style={{
          background:
            "radial-gradient(circle at 0% 0%, rgba(14,165,233,0.12), transparent 50%), radial-gradient(circle at 100% 0%, rgba(34,197,94,0.1), transparent 55%)",
        }}
      />

      {/* Hero */}
      <section className="relative pb-12 pt-2 md:pb-16">
        <div className="grid items-center gap-10 lg:grid-cols-[1.12fr_1fr] lg:gap-12">
          <div>
            <p className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-cyan-700 sm:text-xs">
              DACH · Enterprise · AI Governance
            </p>
            <h1 className="mt-3 text-3xl font-semibold leading-tight tracking-tight text-slate-900 sm:text-4xl lg:text-[2.35rem] lg:leading-[1.12]">
              Der Governance-Layer für Ihre{" "}
              <span className="bg-gradient-to-r from-cyan-700 to-emerald-600 bg-clip-text text-transparent">
                AI- und NIS2-Programme
              </span>
              .
            </h1>
            <p className="mt-4 max-w-xl text-sm leading-relaxed text-slate-600 sm:text-base">
              Eine Plattform für Beratungen und Enterprise-Teams: Unterstützung bei Vorbereitung
              und strukturierter Dokumentation im Kontext von EU AI Act, NIS2 und ISO-Standards –
              mit Board-KPIs, Evidence und Mandantenfähigkeit. Keine Rechtsberatung; konkrete
              Bewertungen verbleiben bei Ihnen und Ihren Beauftragten.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <TrackedContactLink
                href={contactPageHref("home-hero")}
                ctaId="home-hero-demo"
                quelle="home-hero"
                className="inline-flex items-center justify-center rounded-full bg-gradient-to-r from-emerald-600 to-emerald-500 px-5 py-2.5 text-sm font-semibold text-white shadow-md shadow-emerald-900/15 transition hover:from-emerald-700 hover:to-emerald-600"
              >
                Demo anfragen
              </TrackedContactLink>
              <Link
                href="/board/kpis"
                className="inline-flex items-center justify-center rounded-full border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-800 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
              >
                Board öffnen
              </Link>
            </div>
            <p className="mt-6 text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-slate-500 sm:text-xs">
              EU AI Act · NIS2 · ISO 27001/27701 · ISO 42001 · DSGVO
            </p>
          </div>
          <HomeProductPreview />
        </div>
      </section>

      <div className="border-t border-slate-200/80" />

      {/* Drei Gründe */}
      <section className="py-12 md:py-14" aria-labelledby="home-reasons">
        <div className="mx-auto max-w-7xl">
          <SectionTitle
            id="home-reasons"
            title="Drei Gründe, warum Teams auf Compliance Hub setzen."
            subtitle="Gemeinsamer Policy-Layer, echte Mandantenfähigkeit und belastbare Evidence für Audits und Board."
          />
          <div className="grid gap-5 md:grid-cols-3">
            {[
              {
                accent: "bg-cyan-500",
                icon: "🧩",
                title: "Ein Policy-Layer für alle Normen",
                tag: "Framework Graph",
                text: "EU AI Act, ISO 42001, ISO 27001/27701, NIS2 und DSGVO in einem gemeinsamen Kontrollmodell.",
              },
              {
                accent: "bg-indigo-500",
                icon: "👥",
                title: "Berater-ready Plattform",
                tag: "Mandanten-Engine",
                text: "Mandantenfähigkeit, Rollenmodell und exportfähige Reports für skalierbare Beratungsprojekte.",
              },
              {
                accent: "bg-emerald-500",
                icon: "📄",
                title: "Evidence strukturiert bereitstellen",
                tag: "Evidence Engine",
                text: "Gap-Analysen, KI-Register und Board-Reports aus einem gemeinsamen Datenmodell – zur Prüfung und zum Review vorbereitet.",
              },
            ].map((c) => (
              <article
                key={c.title}
                className="relative overflow-hidden rounded-2xl border border-slate-200/90 bg-white p-5 shadow-md shadow-slate-200/40"
              >
                <div className={`absolute inset-x-0 top-0 h-1 ${c.accent}`} aria-hidden />
                <div className="mt-1 flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-lg">
                    {c.icon}
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900 sm:text-[0.95rem]">
                      {c.title}
                    </h3>
                    <p className="text-[0.65rem] font-medium uppercase tracking-wide text-slate-500">
                      {c.tag}
                    </p>
                  </div>
                </div>
                <p className="mt-4 text-sm leading-relaxed text-slate-600">{c.text}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <div className="border-t border-slate-200/80" />

      {/* Datenfluss */}
      <section className="py-12 md:py-14" aria-labelledby="home-flow">
        <div className="mx-auto max-w-7xl">
          <SectionTitle
            id="home-flow"
            title="Ein klarer Datenfluss statt Projekt-Chaos."
            subtitle="Vier Stationen, ein sauberer Flow: Scope, Inventory, Engine und Output – für AI- und Compliance-Daten."
          />
          <div className="relative grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4 lg:gap-4">
            <div
              aria-hidden
              className="pointer-events-none absolute left-[8%] right-[8%] top-8 hidden h-0.5 bg-gradient-to-r from-slate-200 via-slate-300 to-slate-200 lg:block"
            />
            {[
              {
                n: "1",
                t: "Scope",
                sub: "Normen, Standorte, KI-Systeme",
                d: "Mandat, Geltungsbereich und kritische Systeme definieren.",
                icon: "📥",
                ring: "border-cyan-500",
              },
              {
                n: "2",
                t: "Inventory",
                sub: "Assets, Controls, Evidence",
                d: "Daten einspielen – per UI, Import oder API.",
                icon: "📊",
                ring: "border-cyan-500",
              },
              {
                n: "3",
                t: "Engine",
                sub: "Policy & Risiko",
                d: "Violations, Empfehlungen und Prioritäten zusammenführen (unterstützend, keine automatische Rechtsbewertung).",
                icon: "🤖",
                ring: "border-cyan-500",
              },
              {
                n: "4",
                t: "Output",
                sub: "Reports & Nachweise",
                d: "Board-Reports, Auditor-Dossiers und Exporte erzeugen.",
                icon: "📤",
                ring: "border-emerald-500",
              },
            ].map((step) => (
              <div key={step.n} className="relative z-[1] text-center">
                <div
                  className={`mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full border-2 bg-white text-2xl shadow-sm ${step.ring}`}
                >
                  {step.icon}
                </div>
                <div className="text-xs font-semibold text-slate-900 sm:text-sm">
                  {step.n}. {step.t}
                </div>
                <div className="mt-1 text-[0.8rem] text-slate-600">{step.sub}</div>
                <p className="mt-2 text-[0.75rem] leading-relaxed text-slate-500 sm:text-xs">
                  {step.d}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="border-t border-slate-200/80" />

      {/* Integrationen */}
      <section className="py-12 md:py-14" aria-labelledby="home-integrations">
        <div className="mx-auto max-w-7xl">
          <SectionTitle
            id="home-integrations"
            title="Eingebettet in Ihre AI- und Tool-Landschaft."
            subtitle="Anbindung per API, Webhooks oder Workflow-Engine – kompatibel mit gängigen Providern und GRC-Tools."
          />
          <div className="grid grid-cols-[repeat(auto-fill,minmax(140px,1fr))] gap-3 sm:gap-4">
            {[
              { icon: "🤖", name: "OpenAI", sub: "Foundation Models" },
              { icon: "🧠", name: "Anthropic", sub: "LLMs" },
              { icon: "⚙️", name: "Vertex AI", sub: "Cloud AI" },
              { icon: "☁️", name: "Azure AI", sub: "Cloud AI" },
              { icon: "📊", name: "Snowflake", sub: "Data Platform" },
              { icon: "📈", name: "Databricks", sub: "Lakehouse" },
              { icon: "🛡️", name: "OneTrust", sub: "GRC" },
              { icon: "📋", name: "Jira", sub: "Tickets" },
            ].map((p) => (
              <div
                key={p.name}
                className="rounded-xl border border-slate-200/90 bg-white px-3 py-4 text-center shadow-sm transition hover:border-cyan-200/80 hover:shadow-md"
              >
                <span className="text-2xl" aria-hidden>
                  {p.icon}
                </span>
                <div className="mt-2 text-xs font-semibold text-slate-900 sm:text-sm">
                  {p.name}
                </div>
                <div className="mt-0.5 text-[0.65rem] text-slate-500">{p.sub}</div>
              </div>
            ))}
          </div>
          <p className="mt-6 text-center text-xs text-slate-500">
            Ihre Plattform fehlt?{" "}
            <TrackedContactLink
              href={contactPageHref("home-integrations")}
              ctaId="home-integrations-kontakt"
              quelle="home-integrations"
              className="font-medium text-cyan-700 underline-offset-2 hover:underline"
            >
              Kontakt aufnehmen
            </TrackedContactLink>{" "}
            oder über Ihr Compliance-Team.
          </p>
        </div>
      </section>

      <div className="border-t border-slate-200/80" />

      {/* CTA */}
      <section className="py-10 md:py-12">
        <div className="mx-auto max-w-3xl rounded-2xl border border-cyan-200/80 bg-gradient-to-br from-cyan-50/90 via-white to-emerald-50/50 px-6 py-8 text-center shadow-lg shadow-slate-200/50 sm:px-10">
          <h2 className="text-lg font-semibold text-slate-900 sm:text-xl">
            Integration in Ihre Governance-Landschaft besprechen?
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            Wir zeigen, wie Compliance Hub in GRC-Tools, Ticketing, DMS und SIEM passt – und wo
            der größte Hebel liegt. Pakete von AI Act Readiness bis Enterprise Connectors besprechen
            wir gern im Gespräch.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <TrackedContactLink
              href={contactPageHref("home-mid-cta")}
              ctaId="home-mid-cta-demo"
              quelle="home-mid-cta"
              className="inline-flex items-center justify-center rounded-xl bg-gradient-to-r from-emerald-600 to-emerald-500 px-6 py-3 text-sm font-semibold text-white shadow-md transition hover:from-emerald-700 hover:to-emerald-600"
            >
              Demo anfragen
            </TrackedContactLink>
            <Link href="/tenant/compliance-overview" className={`${CH_BTN_SECONDARY} px-6 py-3`}>
              Mandant öffnen
            </Link>
            <Link href="/board/kpis" className={CH_BTN_SECONDARY}>
              Board-Ansicht
            </Link>
          </div>
        </div>
      </section>

      <div className="border-t border-slate-200/80" />

      {/* Security */}
      <section className="py-12 md:pb-4" aria-labelledby="home-security">
        <div className="mx-auto grid max-w-7xl items-start gap-10 lg:grid-cols-[1.05fr_0.95fr]">
          <div>
            <h2
              id="home-security"
              className="text-lg font-semibold tracking-tight text-slate-900 sm:text-xl"
            >
              Security, DSGVO &amp; Hosting in der EU
            </h2>
            <p className="mt-3 max-w-xl text-sm leading-relaxed text-slate-600">
              Für Industrie, Mittelstand und Kanzleien im DACH-Raum: EU-Hosting, klare
              Trennung der Umgebungen und ein Setup, das bei der Einordnung von NIS2, EU AI Act,
              DSGVO sowie ISO 27001/42001 unterstützt.
            </p>
            <ul className="mt-6 flex list-none flex-col gap-3 p-0">
              {[
                "EU-Hosting mit DACH-Fokus: Frontend z. B. auf Vercel (EU-Regionen), Backend und Orchestrierung wahlweise in Deutschland.",
                "PostgreSQL mit Verschlüsselung at Rest, Backups und getrennten Umgebungen (Dev/Staging/Prod) je Mandant.",
                "Mandanten-Isolation (z. B. PostgreSQL RLS), SSO (SAML 2.0, Azure AD, SAP IAS) und Audit-Logs für Board und Prüfer.",
              ].map((line) => (
                <li key={line} className="flex gap-3 text-sm leading-relaxed text-slate-800">
                  <span
                    className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-emerald-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]"
                    aria-hidden
                  />
                  <span>{line}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-2xl border border-slate-200/90 bg-gradient-to-b from-sky-50/80 to-white p-5 shadow-md shadow-slate-200/40">
            <div className="flex justify-between text-xs text-slate-500">
              <span>Infrastruktur-Snapshot</span>
              <span>Architektur</span>
            </div>
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
              {[
                { t: "Vercel", m: "Frontend & Edge", s: "EU-Regionen, TLS" },
                { t: "Postgres", m: "Supabase / Neon", s: "PostgreSQL mit RLS" },
                { t: "Hetzner (DE)", m: "Compute & Storage", s: "DE/EU-Hosting" },
              ].map((b) => (
                <div
                  key={b.t}
                  className="rounded-xl border border-slate-200/80 bg-white/90 p-3 shadow-sm"
                >
                  <div className="text-[0.65rem] font-semibold uppercase tracking-wide text-cyan-800">
                    {b.t}
                  </div>
                  <div className="mt-1 text-sm font-medium text-slate-900">{b.m}</div>
                  <div className="mt-0.5 text-[0.7rem] text-slate-500">{b.s}</div>
                </div>
              ))}
            </div>
            <Link href="/settings" className={`${CH_BTN_PRIMARY} mt-5 w-full sm:w-auto`}>
              Zu Mandant &amp; Einstellungen
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
