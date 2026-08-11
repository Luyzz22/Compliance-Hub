import Link from "next/link";

import { TrackedContactLink } from "@/components/contact/TrackedContactLink";
import { HomeHeroSlides } from "@/components/home/HomeHeroSlides";
import { HomeProductPreview } from "@/components/home/HomeProductPreview";
import { contactPageHref } from "@/lib/publicContact";
import { isPublicSiteRelease } from "@/lib/releaseProfile";

function SectionTitle({
  title,
  subtitle,
  id,
}: {
  title: string;
  subtitle: string;
  id: string;
}) {
  return (
    <div className="max-w-3xl">
      <h2
        id={id}
        className="text-3xl font-semibold leading-[1.08] tracking-[-0.035em] text-[var(--ch-ink)] sm:text-4xl lg:text-[3.25rem]"
      >
        {title}
      </h2>
      <p className="mt-5 max-w-[65ch] text-base leading-8 text-[var(--ch-muted)]">
        {subtitle}
      </p>
    </div>
  );
}

const briefingHref = contactPageHref({
  quelle: "home-hero",
  ctaId: "home-hero-demo",
  ctaLabel: "Demo anfragen",
});

export default function HomePage() {
  const publicSite = isPublicSiteRelease();

  return (
    <div className="home-enterprise relative min-w-0">
      <section className="border-b border-[var(--ch-border)] pb-16 pt-8 sm:pb-20 sm:pt-12 lg:pb-24 lg:pt-16">
        <div className="grid items-center gap-12 lg:grid-cols-[0.9fr_1.1fr] lg:gap-16">
          <header className="max-w-2xl">
            <h1 className="text-4xl font-semibold leading-[0.98] tracking-[-0.04em] text-[var(--ch-ink)] sm:text-5xl lg:text-[3.75rem]">
              KI-Governance, die Entscheidungen belegbar macht.
            </h1>
            <p className="mt-6 max-w-xl text-base leading-8 text-[var(--ch-muted)] sm:text-lg">
              Ein kontrollierter Arbeitsraum für AI-Systeme, Pflichten, Evidence und Human Review im regulierten DACH-Betrieb.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <TrackedContactLink
                href={briefingHref}
                ctaId="home-hero-demo"
                quelle="home-hero"
                trackingEnabled={!publicSite}
                className="home-button-primary"
              >
                Demo anfragen
              </TrackedContactLink>
              <Link href="/trust-center" prefetch={false} className="home-button-secondary">
                Trust Center prüfen
              </Link>
            </div>
          </header>

          <HomeHeroSlides />
        </div>
      </section>

      <section aria-label="Verifizierte Eigenschaften des Public Release" className="border-b border-[var(--ch-border)]">
        <dl className="grid sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Public Release", "Stateless"],
            ["Browser-Schutz", "Strict CSP"],
            ["Freigaben", "Human Review"],
            ["Enterprise-Daten", "Separat gegated"],
          ].map(([label, value], index) => (
            <div
              key={label}
              className={`py-6 sm:px-6 lg:py-7 ${index > 0 ? "sm:border-l sm:border-[var(--ch-border)]" : ""}`}
            >
              <dt className="text-xs font-medium text-[var(--ch-muted)]">{label}</dt>
              <dd className="mt-1 text-base font-semibold tracking-[-0.015em] text-[var(--ch-ink)]">
                {value}
              </dd>
            </div>
          ))}
        </dl>
      </section>

      <section id="home-reasons" className="py-20 sm:py-24 lg:py-32" aria-labelledby="home-model">
        <SectionTitle
          id="home-model"
          title="Von der Pflicht zur verantwortbaren Entscheidung."
          subtitle="Compliance Hub verbindet Regelwerke nicht als Checklisten, sondern als nachvollziehbaren Arbeitsfluss mit Zuständigkeit, Evidence und Review."
        />

        <div id="home-flow" className="mt-14 grid scroll-mt-24 gap-12 lg:grid-cols-[0.72fr_1.28fr] lg:gap-20">
          <div className="max-w-lg">
            <p className="text-xl font-medium leading-8 tracking-[-0.02em] text-[var(--ch-ink)] sm:text-2xl">
              Ein gemeinsames Kontrollmodell für EU AI Act, ISO 42001, ISO 27001/27701, NIS2 und DSGVO.
            </p>
            <p className="mt-5 text-sm leading-7 text-[var(--ch-muted)]">
              Die Plattform bereitet Informationen für qualifizierte Prüfung und Freigabe vor. Sie trifft keine automatische Rechtsentscheidung.
            </p>
          </div>

          <dl className="border-t border-[var(--ch-border-strong)]">
            {[
              ["Scope", "KI-Systeme, Rollen, Standorte und anwendbare Regelwerke werden in einem gemeinsamen Kontext erfasst."],
              ["Controls", "Pflichten werden mit Status, Verantwortlichkeit, Frist und konkretem Handlungsbedarf verbunden."],
              ["Evidence", "Quellen, Änderungen und Reviews bleiben auffindbar, versionierbar und für Exporte strukturiert."],
              ["Decision", "Risiken und offene Maßnahmen werden für Board, Compliance und Betrieb in ihrem Kontext verdichtet."],
            ].map(([term, description]) => (
              <div
                key={term}
                className="grid gap-3 border-b border-[var(--ch-border)] py-6 sm:grid-cols-[8rem_1fr] sm:gap-8"
              >
                <dt className="font-mono text-sm font-semibold text-[var(--ch-accent)]">{term}</dt>
                <dd className="text-sm leading-7 text-[var(--ch-muted)]">{description}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section className="border-y border-[var(--ch-border)] bg-white py-20 sm:py-24 lg:py-32" aria-labelledby="home-workspace">
        <div className="grid items-center gap-14 lg:grid-cols-[1.18fr_0.82fr] lg:gap-20">
          <HomeProductPreview />
          <div>
            <SectionTitle
              id="home-workspace"
              title="Produktlogik, die Prüfung nicht simuliert."
              subtitle="Die interaktive Ansicht zeigt, wie Controls, Evidence und Entscheidungskontext zusammenfinden. Inhalte bleiben illustrativ und klar gekennzeichnet."
            />
            <ul className="mt-9 space-y-5">
              {[
                "Kontrollstatus und Verantwortlichkeit bleiben zusammen sichtbar.",
                "Evidence wird mit Herkunft und Review-Kontext geführt.",
                "Ungeklärte Punkte bleiben offen, statt rechnerisch zu verschwinden.",
              ].map((item) => (
                <li key={item} className="grid grid-cols-[1.25rem_1fr] gap-3 text-sm leading-7 text-[var(--ch-ink-soft)]">
                  <span aria-hidden className="mt-3 h-px bg-[var(--ch-accent)]" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section id="home-integrations" className="py-20 sm:py-24 lg:py-32" aria-labelledby="home-integration">
        <div className="grid gap-14 lg:grid-cols-[0.78fr_1.22fr] lg:gap-20">
          <SectionTitle
            id="home-integration"
            title="Anschlussfähig, ohne Integration vorzutäuschen."
            subtitle="Die Architektur trennt Identität, Daten, AI und operative Übergaben. Produktive Verbindungen werden instanzbezogen freigegeben und dokumentiert."
          />

          <div className="border-t border-[var(--ch-border-strong)]">
            {[
              {
                title: "Identity plane",
                detail: "Microsoft Entra ID, SSO, RBAC und tenant-gebundene Autorisierung",
                state: "Release-Evidence erforderlich",
              },
              {
                title: "AI plane",
                detail: "Azure OpenAI, Managed Identity, PII-Blockierung und tenant-spezifische Policy",
                state: "Standardmäßig deaktiviert",
              },
              {
                title: "Data plane",
                detail: "PostgreSQL, Blob-Speicher, Tenant-Isolation, Retention und Exportpfade",
                state: "Produktionsfreigabe separat",
              },
              {
                title: "Operations plane",
                detail: "APIs, Webhooks, DMS-, SIEM- und Ticketing-Anschluss nach Projektprüfung",
                state: "Keine pauschale Connector-Zusage",
              },
            ].map((item) => (
              <div key={item.title} className="grid gap-3 border-b border-[var(--ch-border)] py-6 sm:grid-cols-[10rem_1fr_auto] sm:items-start sm:gap-6">
                <h3 className="text-sm font-semibold text-[var(--ch-ink)]">{item.title}</h3>
                <p className="text-sm leading-7 text-[var(--ch-muted)]">{item.detail}</p>
                <p className="text-xs font-medium text-[var(--ch-accent)] sm:max-w-36 sm:text-right sm:leading-5">
                  {item.state}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-y border-[var(--ch-border)] bg-[var(--ch-surface-subtle)] py-20 sm:py-24" aria-labelledby="home-security">
        <div className="grid gap-14 lg:grid-cols-[0.82fr_1.18fr] lg:gap-20">
          <div>
            <SectionTitle
              id="home-security"
              title="Enterprise beginnt am Release Gate."
              subtitle="Identität, Datenregion, rechtliche Angaben und technische Kontrollen müssen vor der Enterprise-Freigabe mit datierter Evidence belegt sein."
            />
            <Link href="/trust-center" prefetch={false} className="home-text-link mt-7 inline-flex">
              Freigegebenen Umfang im Trust Center prüfen
            </Link>
          </div>

          <div className="border-t border-[var(--ch-border-strong)]">
            {[
              ["Öffentliche Website", "Aktiv", "Keine Anmeldung, Mandantendaten oder Zustands-APIs"],
              ["Enterprise-Datenebene", "Gegated", "Tenant-, Betriebs- und Datenschutz-Evidence erforderlich"],
              ["Azure OpenAI", "Gegated", "EU-Region oder Data Zone, Managed Identity und Freigabe erforderlich"],
            ].map(([area, state, detail]) => (
              <div key={area} className="grid gap-2 border-b border-[var(--ch-border)] py-6 sm:grid-cols-[1fr_7rem_1.4fr] sm:gap-6">
                <h3 className="text-sm font-semibold text-[var(--ch-ink)]">{area}</h3>
                <p className="font-mono text-xs font-semibold text-[var(--ch-accent)]">{state}</p>
                <p className="text-sm leading-6 text-[var(--ch-muted)]">{detail}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-20 sm:py-24 lg:py-28">
        <div className="grid gap-8 border border-[var(--ch-border-strong)] bg-white px-6 py-10 shadow-[0_24px_70px_rgba(31,35,40,0.08)] sm:px-10 sm:py-12 lg:grid-cols-[1fr_auto] lg:items-center lg:px-14">
          <div>
            <h2 className="text-3xl font-semibold tracking-[-0.035em] text-[var(--ch-ink)] sm:text-4xl">
              Ihre Governance-Architektur konkret prüfen.
            </h2>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-[var(--ch-muted)]">
              Wir ordnen Scope, Evidence, Rollen und Integrationsgrenzen für Ihren konkreten Einsatz ein. Keine Rechtsberatung.
            </p>
          </div>
          <TrackedContactLink
            href={contactPageHref({
              quelle: "home-mid-cta",
              ctaId: "home-mid-cta-demo",
              ctaLabel: "Demo anfragen",
            })}
            ctaId="home-mid-cta-demo"
            quelle="home-mid-cta"
            trackingEnabled={!publicSite}
            className="home-button-primary"
          >
            Demo anfragen
          </TrackedContactLink>
        </div>
      </section>
    </div>
  );
}
