import Link from "next/link";
import React from "react";

import { TrackedContactLink } from "@/components/contact/TrackedContactLink";
import { HomeProductPreview } from "@/components/home/HomeProductPreview";
import { CH_BTN_PRIMARY } from "@/lib/boardLayout";
import { contactPageHref } from "@/lib/publicContact";
import { isPublicSiteRelease } from "@/lib/releaseProfile";

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
    <div className="mb-10 max-w-3xl">
      <h2
        id={id}
        className="text-2xl font-semibold tracking-[-0.035em] text-[#07111f] sm:text-3xl"
      >
        {title}
      </h2>
      <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600 sm:text-base">
        {subtitle}
      </p>
    </div>
  );
}

export default function HomePage() {
  const publicSite = isPublicSiteRelease();

  return (
    <div className="relative min-w-0">
      <div
        aria-hidden
        className="enterprise-grid pointer-events-none fixed inset-0 -z-20 opacity-70"
      />
      <div
        aria-hidden
        className="enterprise-ambient pointer-events-none fixed inset-0 -z-10 opacity-80"
      />

      {/* Hero */}
      <section className="relative pb-20 pt-6 md:pb-28 md:pt-12">
        <div className="grid items-center gap-14 lg:grid-cols-[1.08fr_0.92fr] lg:gap-20">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full border border-slate-200/80 bg-white/70 px-3 py-1.5 text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-slate-700 shadow-sm backdrop-blur sm:text-xs">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden />
              DACH · Enterprise AI Governance
            </p>
            <h1 className="mt-6 max-w-4xl text-4xl font-semibold leading-[0.98] tracking-[-0.055em] text-[#07111f] sm:text-5xl lg:text-[4.5rem]">
              Governance, die mit Ihrer AI-Infrastruktur skaliert.
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-7 text-slate-600 sm:text-lg sm:leading-8">
              Ein kontrollierter Arbeitsraum für AI-Systeme, Risiken, Controls und Evidence –
              mandantenfähig, nachvollziehbar und für EU AI Act, NIS2 sowie ISO 42001
              vorbereitet. Fachliche Entscheidungen bleiben bei den verantwortlichen Personen.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <TrackedContactLink
                href={contactPageHref({
                  quelle: "home-hero",
                  ctaId: "home-hero-demo",
                  ctaLabel: "Demo anfragen",
                })}
                ctaId="home-hero-demo"
                quelle="home-hero"
                trackingEnabled={!publicSite}
                className="inline-flex min-h-12 items-center justify-center rounded-full bg-[#07111f] px-6 py-3 text-sm font-semibold text-white shadow-xl shadow-slate-950/15 transition hover:-translate-y-0.5 hover:bg-slate-800"
              >
                Demo anfragen
              </TrackedContactLink>
              <Link
                href="/trust-center"
                className="inline-flex min-h-12 items-center justify-center rounded-full border border-slate-200 bg-white/85 px-6 py-3 text-sm font-semibold text-slate-900 shadow-sm transition hover:-translate-y-0.5 hover:border-slate-300"
              >
                Trust Center
              </Link>
              {!publicSite ? (
                <Link
                  href="/board/kpis"
                  className="inline-flex min-h-12 items-center justify-center rounded-full px-5 py-3 text-sm font-semibold text-slate-600 transition hover:text-slate-950"
                >
                  Board öffnen
                </Link>
              ) : null}
            </div>
            <p className="mt-8 text-[0.65rem] font-semibold uppercase tracking-[0.16em] text-slate-500 sm:text-xs">
              EU AI Act · NIS2 · ISO 27001/27701 · ISO 42001 · DSGVO
            </p>
          </div>
          <HomeProductPreview />
        </div>
      </section>

      <div className="border-t border-slate-200/80" />

      {/* Drei Gründe */}
      <section className="py-20 md:py-28" aria-labelledby="home-reasons">
        <div className="mx-auto max-w-7xl">
          <SectionTitle
            id="home-reasons"
            title="Drei Gründe, warum Teams auf Compliance Hub setzen."
            subtitle="Gemeinsamer Policy-Layer, echte Mandantenfähigkeit und belastbare Evidence für Audits und Board."
          />
          <div className="grid gap-5 md:grid-cols-3">
            {[
              {
                index: "01",
                title: "Ein Policy-Layer für alle Normen",
                tag: "Framework Graph",
                text: "EU AI Act, ISO 42001, ISO 27001/27701, NIS2 und DSGVO in einem gemeinsamen Kontrollmodell.",
              },
              {
                index: "02",
                title: "Berater-ready Plattform",
                tag: "Mandanten-Engine",
                text: "Mandantenfähigkeit, Rollenmodell und exportfähige Reports für skalierbare Beratungsprojekte.",
              },
              {
                index: "03",
                title: "Evidence strukturiert bereitstellen",
                tag: "Evidence Engine",
                text: "Gap-Analysen, KI-Register und Board-Reports aus einem gemeinsamen Datenmodell – zur Prüfung und zum Review vorbereitet.",
              },
            ].map((c) => (
              <article
                key={c.title}
                className="premium-surface group relative overflow-hidden rounded-[1.75rem] p-7 transition duration-300 hover:-translate-y-1"
              >
                <div className="flex items-center gap-3">
                  <div className="font-mono text-xs font-semibold text-blue-600">{c.index}</div>
                  <div>
                    <h3 className="text-base font-semibold tracking-[-0.02em] text-slate-950">
                      {c.title}
                    </h3>
                    <p className="text-[0.65rem] font-medium uppercase tracking-wide text-slate-500">
                      {c.tag}
                    </p>
                  </div>
                </div>
                <p className="mt-5 text-sm leading-7 text-slate-600">{c.text}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <div className="border-t border-slate-200/80" />

      {/* Datenfluss */}
      <section className="py-20 md:py-28" aria-labelledby="home-flow">
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
                ring: "border-cyan-500",
              },
              {
                n: "2",
                t: "Inventory",
                sub: "Assets, Controls, Evidence",
                d: "Daten einspielen – per UI, Import oder API.",
                ring: "border-cyan-500",
              },
              {
                n: "3",
                t: "Engine",
                sub: "Policy & Risiko",
                d: "Violations, Empfehlungen und Prioritäten zusammenführen (unterstützend, keine automatische Rechtsbewertung).",
                ring: "border-cyan-500",
              },
              {
                n: "4",
                t: "Output",
                sub: "Reports & Nachweise",
                d: "Board-Reports, Auditor-Dossiers und Exporte erzeugen.",
                ring: "border-emerald-500",
              },
            ].map((step) => (
              <div key={step.n} className="relative z-[1] text-center">
                <div
                  className={`mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border bg-white font-mono text-sm font-semibold text-slate-950 shadow-sm ${step.ring}`}
                >
                  0{step.n}
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
      <section className="py-20 md:py-28" aria-labelledby="home-integrations">
        <div className="mx-auto max-w-7xl">
          <SectionTitle
            id="home-integrations"
            title="Eingebettet in Ihre AI- und Tool-Landschaft."
            subtitle="Anbindung per API, Webhooks oder Workflow-Engine – kompatibel mit gängigen Providern und GRC-Tools."
          />
          <div className="grid grid-cols-[repeat(auto-fill,minmax(140px,1fr))] gap-3 sm:gap-4">
            {[
              { mark: "OA", name: "OpenAI", sub: "Foundation Models" },
              { mark: "AN", name: "Anthropic", sub: "LLMs" },
              { mark: "VX", name: "Vertex AI", sub: "Cloud AI" },
              { mark: "AZ", name: "Azure AI", sub: "EU AI Plane" },
              { mark: "SF", name: "Snowflake", sub: "Data Platform" },
              { mark: "DB", name: "Databricks", sub: "Lakehouse" },
              { mark: "OT", name: "OneTrust", sub: "GRC" },
              { mark: "JR", name: "Jira", sub: "Tickets" },
            ].map((p) => (
              <div
                key={p.name}
                className="premium-surface rounded-2xl px-3 py-5 text-center transition hover:-translate-y-0.5"
              >
                <span className="mx-auto flex h-9 w-9 items-center justify-center rounded-xl bg-slate-950 font-mono text-[0.65rem] font-semibold text-white" aria-hidden>
                  {p.mark}
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
              href={contactPageHref({
                quelle: "home-integrations",
                ctaId: "home-integrations-kontakt",
                ctaLabel: "Kontakt aufnehmen",
              })}
              ctaId="home-integrations-kontakt"
              quelle="home-integrations"
              trackingEnabled={!publicSite}
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
      <section className="py-20 md:py-28">
        <div className="mx-auto max-w-5xl overflow-hidden rounded-[2rem] bg-[#07111f] px-6 py-12 text-center text-white shadow-2xl shadow-slate-950/20 sm:px-12 md:py-16">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-300">Enterprise briefing</p>
          <h2 className="mt-3 text-2xl font-semibold tracking-[-0.035em] text-white sm:text-3xl">
            Integration in Ihre Governance-Landschaft besprechen?
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-7 text-slate-300">
            Wir zeigen, wie Compliance Hub in GRC-Tools, Ticketing, DMS und SIEM passt – und wo
            der größte Hebel liegt. Pakete von AI Act Readiness bis Enterprise Connectors besprechen
            wir gern im Gespräch.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <TrackedContactLink
              href={contactPageHref({
                quelle: "home-mid-cta",
                ctaId: "home-mid-cta-demo",
                ctaLabel: "Demo anfragen",
              })}
              ctaId="home-mid-cta-demo"
              quelle="home-mid-cta"
              trackingEnabled={!publicSite}
              className="inline-flex items-center justify-center rounded-full bg-white px-6 py-3 text-sm font-semibold text-slate-950 shadow-md transition hover:-translate-y-0.5"
            >
              Demo anfragen
            </TrackedContactLink>
            {!publicSite ? (
              <>
                <Link href="/auth/login" className="inline-flex items-center justify-center rounded-full border border-white/20 bg-white/10 px-6 py-3 text-sm font-semibold text-white transition hover:bg-white/15">
                  Anmelden
                </Link>
                <Link href="/board/kpis" className="inline-flex items-center justify-center rounded-full px-5 py-3 text-sm font-semibold text-slate-300 transition hover:text-white">
                  Board-Ansicht
                </Link>
              </>
            ) : null}
          </div>
        </div>
      </section>

      <div className="border-t border-slate-200/80" />

      {/* Security */}
      <section className="py-20 md:pb-12 md:pt-28" aria-labelledby="home-security">
        <div className="mx-auto grid max-w-7xl items-start gap-10 lg:grid-cols-[1.05fr_0.95fr]">
          <div>
            <h2
              id="home-security"
              className="text-lg font-semibold tracking-tight text-slate-900 sm:text-xl"
            >
              Security und Datenschutz als Release Gate
            </h2>
            <p className="mt-3 max-w-xl text-sm leading-relaxed text-slate-600">
              Produktivbetrieb wird nur freigegeben, wenn Identität, Datenregion, rechtliche
              Angaben und technische Kontrollen nachweislich konfiguriert sind.
            </p>
            <ul className="mt-6 flex list-none flex-col gap-3 p-0">
              {[
                "Azure OpenAI ist nur nach EU-Region-/Data-Zone-Attestierung aktiv; Managed Identity ist der Produktionsstandard.",
                "LLM-Funktionen sind standardmäßig aus. Personenbezogene Daten und Prompt-Injection-Muster werden vor Modellaufrufen blockiert.",
                "Produktive Builds scheitern bei fehlenden Legal-, Auth-, Host-, Tenant- oder Datenschutzfreigaben bewusst.",
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
          <div className="premium-surface rounded-[1.75rem] p-6">
            <div className="flex justify-between text-xs text-slate-500">
              <span>Infrastruktur-Snapshot</span>
              <span>Architektur</span>
            </div>
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
              {[
                { t: "Identity plane", m: "SSO & RBAC", s: "Release-gated" },
                { t: "Data plane", m: "Tenant isolation", s: "Evidence required" },
                { t: "AI plane", m: "Azure OpenAI", s: "Managed Identity" },
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
            <Link
              href={publicSite ? "/trust-center" : "/settings"}
              className={`${CH_BTN_PRIMARY} mt-5 w-full sm:w-auto`}
            >
              {publicSite ? "Zum Trust Center" : "Zu Mandant & Einstellungen"}
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
