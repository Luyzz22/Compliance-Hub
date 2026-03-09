// src/app/page.tsx
'use client';

import React from 'react';

// Farben: Dark SaaS + klare Akzente, angelehnt an Enterprise/Apple UI
const colors = {
  bgBody: '#020617',
  bgPanel: '#02081B',
  bgPanelSoft: '#050B1F',
  border: '#0F172A',
  accentBlue: '#0EA5E9',
  accentGreen: '#22C55E',
  text: '#E5E7EB',
  textMuted: '#9CA3AF',
  warning: '#F97316',
};

const layout = {
  maxWidth: '1040px',
  sidePadding: '24px',
};

// Hero-Slides
const heroSlides = [
  {
    label: 'EU AI Act, ISO 42001',
    title: 'AI‑Governance ohne Excel‑Chaos.',
    body: 'AI‑System‑Register, Risikoklassifizierung und Technical File in einer gemeinsamen Oberfläche.',
  },
  {
    label: 'NIS2 & ISO 27001',
    title: 'Cyber‑Governance mit Board‑Reife.',
    body: 'Risiko‑ und Maßnahmenübersicht, die direkt in Vorstands‑Reports übersetzbar ist.',
  },
  {
    label: 'Berater‑first',
    title: 'Eine Mandantenplattform statt zehn Tools.',
    body: 'Mandantenfähig, White‑Label‑Reports und wiederverwendbare Kontrollbausteine für jede Norm.',
  },
];

const features = [
  {
    tag: 'Framework Graph',
    title: 'Ein Policy‑Layer für alle Normen',
    body: 'EU AI Act, ISO 42001, ISO 27001/27701, NIS2 & DSGVO in einem gemeinsamen Kontrollmodell.',
  },
  {
    tag: 'Mandanten‑Engine',
    title: 'Berater‑ready Plattform',
    body: 'Mandantenfähigkeit, Rollenmodell und exportfähige Reports für skalierbare Beratungsprojekte.',
  },
  {
    tag: 'Evidence Engine',
    title: 'Evidence auf Knopfdruck',
    body: 'Gap‑Analysen, KI‑Register und Board‑Reports entstehen automatisch aus einem zentralen Datenmodell.',
  },
];

const miniStats = [
  { label: 'AI‑Systeme im Register', value: '27' },
  { label: 'Offene Violations', value: '9', warn: true },
  { label: 'NIS2‑Risiken high+', value: '5' },
  { label: 'Evidence Coverage (Cross‑Framework)', value: '91 %' },
];

function Page() {
  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: colors.bgBody,
        color: colors.text,
        fontFamily:
          'system-ui, -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif',
      }}
    >
      <BackgroundGlow />
      <Header />
      <main>
        <Hero />
        <Divider />
        <FeaturesSection />
        <Divider />
        <FlowSection />
        <Divider />
        <IntegrationsSection />
        <Divider />
        <CTASection />
      </main>
      <SecuritySection />
      <Footer />
    </div>
  );
}

/* Background */

function BackgroundGlow() {
  return (
    <div
      aria-hidden="true"
      style={{
        position: 'fixed',
        inset: 0,
        pointerEvents: 'none',
        background:
          'radial-gradient(circle at 0% 0%, rgba(14,165,233,0.18), transparent 55%), radial-gradient(circle at 100% 0%, rgba(34,197,94,0.16), transparent 60%)',
        opacity: 0.9,
        zIndex: 0,
      }}
    />
  );
}

/* Header */

function Header() {
  return (
    <header
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 10,
        backdropFilter: 'blur(18px)',
        WebkitBackdropFilter: 'blur(18px)',
        background:
          'linear-gradient(to bottom, rgba(2,6,23,0.96), rgba(2,6,23,0.86), transparent)',
        borderBottom: `1px solid ${colors.border}`,
      }}
    >
      <div
        style={{
          maxWidth: layout.maxWidth,
          margin: '0 auto',
          padding: '10px 16px 8px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 16,
        }}
      >
        <BrandMark />
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            style={{
              fontSize: 12,
              padding: '6px 10px',
              borderRadius: 999,
              border: `1px solid ${colors.border}`,
              backgroundColor: 'transparent',
              color: colors.text,
            }}
          >
            Produkt‑Deck
          </button>
          <button
            style={{
              fontSize: 12,
              padding: '6px 12px',
              borderRadius: 999,
              border: 'none',
              background:
                'linear-gradient(135deg, #22C55E, #4ADE80, #22C55E)',
              color: '#020617',
              fontWeight: 600,
            }}
          >
            Early‑Access anfragen
          </button>
        </div>
      </div>
    </header>
  );
}

function BrandMark() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: 999,
          background:
            'conic-gradient(from 220deg, #0EA5E9, #22C55E, #6366F1, #0EA5E9)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 0 0 1px rgba(15,23,42,0.8)',
        }}
      >
        <div
          style={{
            width: 18,
            height: 18,
            borderRadius: 999,
            backgroundColor: colors.bgBody,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 10,
            fontWeight: 700,
            color: colors.accentBlue,
          }}
        >
          CH
        </div>
      </div>
      <div>
        <div
          style={{
            fontWeight: 600,
            fontSize: 14,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
          }}
        >
          Compliance Hub
        </div>
        <div style={{ fontSize: 11, color: colors.textMuted }}>
          Policy Engine für EU AI Act, NIS2, ISO &amp; DSGVO
        </div>
      </div>
    </div>
  );
}

/* Hero mit Slides */

function Hero() {
  const [active, setActive] = React.useState(0);

  return (
    <section
      style={{
        position: 'relative',
        zIndex: 1,
        padding: '40px 0 30px',
      }}
    >
      <div
        style={{
          maxWidth: layout.maxWidth,
          margin: '0 auto',
          padding: `0 ${layout.sidePadding}`,
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1.15fr) minmax(0, 1fr)',
          gap: 28,
          alignItems: 'center',
        }}
      >
        {/* Text-Spalte */}
        <div>
          <p
            style={{
              fontSize: 11,
              letterSpacing: '0.18em',
              textTransform: 'uppercase',
              color: colors.accentBlue,
              marginBottom: 8,
            }}
          >
            DACH · Enterprise · AI Governance
          </p>
          <h1
            style={{
              fontSize: 32,
              lineHeight: 1.1,
              marginBottom: 12,
              fontWeight: 600,
            }}
          >
            Der Governance‑Layer für Ihre{' '}
            <span style={{ color: colors.accentGreen }}>
              AI‑ und NIS2‑Programme
            </span>
            .
          </h1>
          <p
            style={{
              fontSize: 14,
              lineHeight: 1.5,
              color: colors.textMuted,
              maxWidth: 480,
              marginBottom: 16,
            }}
          >
            Eine Plattform, die Beratungen und Enterprise‑Teams nutzen, um EU AI
            Act, NIS2 und ISO‑Standards sicher und nachvollziehbar umzusetzen.
          </p>

          <div
            style={{
              display: 'flex',
              gap: 10,
              flexWrap: 'wrap',
              marginBottom: 12,
            }}
          >
            <button
              style={{
                fontSize: 13,
                padding: '8px 16px',
                borderRadius: 999,
                border: 'none',
                background:
                  'linear-gradient(135deg, #22C55E, #4ADE80, #22C55E)',
                color: '#020617',
                fontWeight: 600,
              }}
            >
              Live‑Demo buchen
            </button>
            <button
              style={{
                fontSize: 13,
                padding: '8px 14px',
                borderRadius: 999,
                border: `1px solid ${colors.border}`,
                backgroundColor: 'rgba(15,23,42,0.88)',
                color: colors.text,
              }}
            >
              5‑Minuten Produkt‑Tour
            </button>
          </div>

          <p
            style={{
              fontSize: 11,
              textTransform: 'uppercase',
              letterSpacing: '0.14em',
              color: colors.textMuted,
            }}
          >
            EU AI Act · NIS2 · ISO 27001/27701 · ISO 42001 · DSGVO
          </p>
        </div>

        {/* Visual-Spalte mit Slides + Stats */}
        <HeroVisual active={active} setActive={setActive} />
      </div>
    </section>
  );
}

function HeroVisual({
  active,
  setActive,
}: {
  active: number;
  setActive: (i: number) => void;
}) {
  return (
    <div
      style={{
        borderRadius: 18,
        border: `1px solid ${colors.border}`,
        background:
          'radial-gradient(circle at 0% 0%, rgba(14,165,233,0.22), rgba(2,6,23,0.98))',
        padding: 14,
        boxShadow: '0 18px 60px rgba(0,0,0,0.7)',
        fontSize: 11,
      }}
    >
      {/* Kopf */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          color: colors.textMuted,
          marginBottom: 8,
        }}
      >
        <span>Musterindustrie Demo GmbH</span>
        <span style={{ color: colors.accentBlue }}>Policy Engine</span>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateRows: 'auto auto',
          gap: 10,
        }}
      >
        {/* Framework-Zeile */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
            gap: 6,
          }}
        >
          {['EU AI Act', 'ISO 42001', 'ISO 27001', 'NIS2'].map(
            (label, idx) => (
              <div
                key={label}
                style={{
                  borderRadius: 10,
                  padding: '6px 6px',
                  border: `1px solid ${colors.border}`,
                  background:
                    idx === 0
                      ? 'linear-gradient(135deg, rgba(14,165,233,0.45), rgba(2,6,23,0.95))'
                      : 'rgba(15,23,42,0.94)',
                  color: idx === 0 ? colors.text : colors.textMuted,
                  fontSize: 10,
                }}
              >
                <div style={{ marginBottom: 4 }}>{label}</div>
                <div
                  style={{
                    height: 4,
                    borderRadius: 999,
                    background:
                      idx === 0
                        ? 'linear-gradient(90deg, #0EA5E9, #22C55E)'
                        : 'linear-gradient(90deg, #1F2937, #020617)',
                  }}
                />
              </div>
            ),
          )}
        </div>

        {/* Slide-Container */}
        <div
          style={{
            borderRadius: 12,
            backgroundColor: colors.bgPanel,
            border: `1px solid ${colors.border}`,
            padding: 10,
          }}
        >
          {/* Tabs */}
          <div
            style={{
              display: 'flex',
              gap: 6,
              marginBottom: 8,
              flexWrap: 'wrap',
            }}
          >
            {heroSlides.map((slide, idx) => {
              const isActive = idx === active;
              return (
                <button
                  key={slide.label}
                  type="button"
                  onClick={() => setActive(idx)}
                  style={{
                    borderRadius: 999,
                    border: isActive
                      ? 'none'
                      : `1px solid ${colors.border}`,
                    padding: '4px 8px',
                    fontSize: 10,
                    cursor: 'pointer',
                    background: isActive
                      ? `linear-gradient(135deg, ${colors.accentBlue}, ${colors.accentGreen})`
                      : 'transparent',
                    color: isActive ? '#020617' : colors.textMuted,
                  }}
                >
                  {slide.label}
                </button>
              );
            })}
          </div>

          {/* Aktive Slide */}
          <div>
            <div
              style={{
                fontSize: 13,
                fontWeight: 600,
                marginBottom: 4,
              }}
            >
              {heroSlides[active].title}
            </div>
            <p
              style={{
                fontSize: 11,
                color: colors.textMuted,
                marginBottom: 8,
              }}
            >
              {heroSlides[active].body}
            </p>

            {/* kleine Kennzahlen-Leiste */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
                gap: 6,
                fontSize: 10,
              }}
            >
              <MetricChip label="Controls compliant" value="214 / 238" />
              <MetricChip label="Offene Violations" value="9" warn />
              <MetricChip label="Board‑Readiness" value="in 2 Tagen" />
            </div>
          </div>
        </div>
      </div>

      {/* Mini-Stats unten – inspiriert von den „Tiles“ aus deiner Integrations‑Page */}
      <div
        style={{
          marginTop: 10,
          display: 'grid',
          gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
          gap: 6,
        }}
      >
        {miniStats.map((s) => (
          <div
            key={s.label}
            style={{
              borderRadius: 10,
              border: `1px solid ${colors.border}`,
              padding: '5px 6px',
              backgroundColor: colors.bgPanelSoft,
              textAlign: 'center',
            }}
          >
            <div
              style={{
                fontSize: 9,
                color: colors.textMuted,
                marginBottom: 2,
              }}
            >
              {s.label}
            </div>
            <div
              style={{
                fontSize: 12,
                fontWeight: 600,
                color: s.warn ? colors.warning : colors.text,
              }}
            >
              {s.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function MetricChip(props: { label: string; value: string; warn?: boolean }) {
  const { label, value, warn } = props;
  return (
    <div
      style={{
        borderRadius: 999,
        border: `1px solid ${colors.border}`,
        padding: '4px 8px',
        backgroundColor: 'rgba(15,23,42,0.9)',
        display: 'flex',
        justifyContent: 'space-between',
        gap: 6,
      }}
    >
      <span style={{ color: colors.textMuted }}>{label}</span>
      <span
        style={{
          color: warn ? colors.warning : colors.text,
          fontWeight: 500,
        }}
      >
        {value}
      </span>
    </div>
  );
}

/* Divider */

function Divider() {
  return (
    <div
      style={{
        borderTop: `1px solid ${colors.border}`,
        opacity: 0.9,
      }}
    />
  );
}

/* Features – Cards angelehnt an .ig-card, aber im Dark-Theme */

function FeaturesSection() {
  return (
    <section style={{ padding: '26px 0' }}>
      <div
        style={{
          maxWidth: layout.maxWidth,
          margin: '0 auto',
          padding: `0 ${layout.sidePadding}`,
        }}
      >
        <h2
          style={{
            fontSize: 16,
            marginBottom: 8,
            fontWeight: 500,
          }}
        >
          Drei Gründe, warum Teams auf Compliance Hub wechseln.
        </h2>
        <p
          style={{
            fontSize: 13,
            color: colors.textMuted,
            maxWidth: 540,
            marginBottom: 16,
          }}
        >
          Fokus auf die Kern‑Pullfaktoren: ein gemeinsamer Policy‑Layer, echte
          Mandantenfähigkeit und belastbare Evidence für Audits & Board.
        </p>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
            gap: 16,
          }}
        >
          {features.map((f) => (
            <div
              key={f.title}
              style={{
                position: 'relative',
                borderRadius: 16,
                border: `1px solid ${colors.border}`,
                backgroundColor: colors.bgPanel,
                padding: 16,
                fontSize: 12,
                overflow: 'hidden',
              }}
            >
              {/* obere Farbleiste – wie .ig-card::before */}
              <div
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  height: 3,
                  background:
                    f.tag === 'Framework Graph'
                      ? colors.accentBlue
                      : f.tag === 'Evidence Engine'
                      ? colors.accentGreen
                      : '#6366F1',
                }}
              />
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  marginBottom: 10,
                }}
              >
                <div
                  style={{
                    width: 26,
                    height: 26,
                    borderRadius: 999,
                    backgroundColor: colors.bgPanelSoft,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 14,
                  }}
                >
                  {f.tag === 'Framework Graph' && '🧩'}
                  {f.tag === 'Mandanten‑Engine' && '👥'}
                  {f.tag === 'Evidence Engine' && '📄'}
                </div>
                <div>
                  <div
                    style={{
                      fontSize: 13,
                      fontWeight: 600,
                    }}
                  >
                    {f.title}
                  </div>
                  <div
                    style={{
                      fontSize: 10,
                      color: colors.textMuted,
                    }}
                  >
                    {f.tag}
                  </div>
                </div>
              </div>
              <p
                style={{
                  fontSize: 12,
                  color: colors.textMuted,
                  lineHeight: 1.5,
                }}
              >
                {f.body}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* Flow – „Datenfluss“-Inspiration mit runden Icons & Linie */

function FlowSection() {
  const steps = [
    {
      icon: '📥',
      title: 'Scope',
      subtitle: 'Normen, Standorte, AI‑Systeme',
      desc: 'Mandat, Geltungsbereich und kritische Systeme definieren.',
    },
    {
      icon: '📊',
      title: 'Inventory',
      subtitle: 'Assets, Controls, Evidence',
      desc: 'Daten einspeisen – via UI, Import oder API.',
    },
    {
      icon: '🤖',
      title: 'Engine',
      subtitle: 'Policy & Risiko',
      desc: 'Violations, Empfehlungen und Prioritäten berechnen.',
    },
    {
      icon: '📤',
      title: 'Output',
      subtitle: 'Reports & Nachweise',
      desc: 'Board‑Reports, Auditor‑Dossiers und Exporte erzeugen.',
    },
  ];

  return (
    <section style={{ padding: '26px 0 32px' }}>
      <div
        style={{
          maxWidth: layout.maxWidth,
          margin: '0 auto',
          padding: `0 ${layout.sidePadding}`,
        }}
      >
        <h2
          style={{
            fontSize: 16,
            marginBottom: 8,
            fontWeight: 500,
          }}
        >
          Ein klarer Datenfluss statt Projekt‑Chaos.
        </h2>
        <p
          style={{
            fontSize: 13,
            color: colors.textMuted,
            maxWidth: 600,
            marginBottom: 18,
          }}
        >
          Wie in deiner Integrations‑Page: vier Stationen, ein sauberer Flow –
          nur eben für AI‑ und Compliance‑Daten statt Belege & Workflows.
        </p>

        {/* Flow-Linie + runde Steps, inspiriert von .ig-flow */}
        <div
          style={{
            position: 'relative',
            display: 'grid',
            gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
            gap: 0,
            padding: '6px 0 0',
          }}
        >
          <div
            aria-hidden="true"
            style={{
              position: 'absolute',
              top: '32px',
              left: '8%',
              right: '8%',
              height: 2,
              background:
                'linear-gradient(to right, rgba(148,163,184,0.3), rgba(148,163,184,0.8), rgba(148,163,184,0.3))',
              zIndex: 0,
            }}
          />
          {steps.map((s, idx) => (
            <div
              key={s.title}
              style={{
                textAlign: 'center',
                position: 'relative',
                zIndex: 1,
                paddingInline: 4,
              }}
            >
              <div
                style={{
                  width: 56,
                  height: 56,
                  borderRadius: '50%',
                  backgroundColor: colors.bgPanel,
                  border: `2px solid ${
                    idx === 3 ? colors.accentGreen : colors.accentBlue
                  }`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 8px',
                  fontSize: 24,
                }}
              >
                {s.icon}
              </div>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  marginBottom: 2,
                }}
              >
                {idx + 1}. {s.title}
              </div>
              <div
                style={{
                  fontSize: 11,
                  color: colors.textMuted,
                  marginBottom: 2,
                }}
              >
                {s.subtitle}
              </div>
              <div
                style={{
                  fontSize: 10,
                  color: colors.textMuted,
                }}
              >
                {s.desc}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function IntegrationsSection() {
  const tools = [
    { icon: '🤖', name: 'OpenAI', cat: 'Foundation Models' },
    { icon: '🧠', name: 'Anthropic', cat: 'LLMs' },
    { icon: '⚙️', name: 'Vertex AI', cat: 'Cloud AI' },
    { icon: '☁️', name: 'Azure AI', cat: 'Cloud AI' },
    { icon: '📊', name: 'Snowflake', cat: 'Data Platform' },
    { icon: '📈', name: 'Databricks', cat: 'Lakehouse' },
    { icon: '🛡️', name: 'OneTrust', cat: 'GRC' },
    { icon: '📋', name: 'Jira', cat: 'Tickets' },
  ];

  return (
    <section style={{ padding: '26px 0 24px' }}>
      <div
        style={{
          maxWidth: layout.maxWidth,
          margin: '0 auto',
          padding: `0 ${layout.sidePadding}`,
        }}
      >
        <h2
          style={{
            fontSize: 16,
            marginBottom: 8,
            fontWeight: 500,
          }}
        >
          Eingebettet in Ihre AI‑ & Tool‑Landschaft.
        </h2>
        <p
          style={{
            fontSize: 13,
            color: colors.textMuted,
            maxWidth: 620,
            marginBottom: 16,
          }}
        >
          Compliance Hub hängt nicht in der Luft: AI‑Provider, Data‑Plattformen und
          bestehende GRC‑Tools werden angebunden – per API, Webhooks oder
          Workflow‑Engine.
        </p>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))',
            gap: 12,
          }}
        >
          {tools.map((t) => (
            <div
              key={t.name}
              style={{
                backgroundColor: colors.bgPanel,
                border: `1px solid ${colors.border}`,
                borderRadius: 12,
                padding: 14,
                textAlign: 'center',
                transition: 'box-shadow 0.2s ease, transform 0.2s ease',
              }}
            >
              <div
                style={{
                  fontSize: 22,
                  marginBottom: 6,
                  display: 'block',
                }}
              >
                {t.icon}
              </div>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: colors.text,
                }}
              >
                {t.name}
              </div>
              <div
                style={{
                  fontSize: 10,
                  color: colors.textMuted,
                  marginTop: 2,
                }}
              >
                {t.cat}
              </div>
            </div>
          ))}
        </div>

        <p
          style={{
            fontSize: 11,
            color: colors.textMuted,
            textAlign: 'center',
            marginTop: 14,
          }}
        >
          Ihre Plattform fehlt?{' '}
          <span style={{ color: colors.accentBlue }}>
            Kontakt aufnehmen &amp; Integration besprechen
          </span>
        </p>
      </div>
    </section>
  );
}

/* CTA */

function CTASection() {
  return (
    <section style={{ padding: '20px 0 26px' }}>
      <div
        style={{
          maxWidth: layout.maxWidth,
          margin: '0 auto',
          padding: `0 ${layout.sidePadding}`,
          borderRadius: 18,
          border: `1px solid ${colors.border}`,
          background:
            'linear-gradient(135deg, rgba(14,165,233,0.22), rgba(2,6,23,0.98))',
          paddingInline: 20,
          paddingBlock: 16,
          textAlign: 'center',
          fontSize: 13,
        }}
      >
        <h2
          style={{
            fontSize: 16,
            marginBottom: 6,
            fontWeight: 500,
          }}
        >
          Integration in Ihre Governance‑Landschaft besprechen?
        </h2>
        <p
          style={{
            color: colors.textMuted,
            fontSize: 12,
            marginBottom: 16,
          }}
        >
          Wir zeigen, wie Compliance Hub in bestehende Strukturen (GRC‑Tools,
          Ticketing, DMS, SIEM) passt – und wo es den größten Hebel bringt.
        </p>
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            gap: 12,
            flexWrap: 'wrap',
          }}
        >
          <button
            style={{
              padding: '10px 26px',
              borderRadius: 10,
              fontSize: 13,
              fontWeight: 600,
              border: 'none',
              background:
                'linear-gradient(135deg, #22C55E, #4ADE80, #22C55E)',
              color: '#020617',
            }}
          >
            Gespräch vereinbaren →
          </button>
          <button
            style={{
              padding: '10px 24px',
              borderRadius: 10,
              fontSize: 13,
              fontWeight: 600,
              background: 'transparent',
              border: `2px solid ${colors.accentBlue}`,
              color: colors.accentBlue,
            }}
          >
            Produkt‑Deck ansehen
          </button>
        </div>
      </div>
    </section>
  );
}


/* Security & Hosting */

function SecuritySection() {
  const bullets = [
    'EU‑Hosting mit DACH‑Fokus: Frontend auf Vercel (EU‑Regionen), Backend & Orchestrierung wahlweise auf Hetzner in Deutschland.',
    'PostgreSQL mit Verschlüsselung at Rest, täglichen Backups und getrennten Umgebungen (Dev/Staging/Prod) je Mandant.',
    'Mandanten‑Isolation via PostgreSQL RLS, SSO‑Integration (SAML 2.0, Azure AD, SAP IAS) und Audit‑Logs für Board & Prüfer.',
  ];

  return (
    <section style={{ padding: '26px 0 24px' }}>
      <div
        style={{
          maxWidth: layout.maxWidth,
          margin: '0 auto',
          padding: `0 ${layout.sidePadding}`,
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1.1fr) minmax(0, 0.9fr)',
          gap: 20,
          alignItems: 'center',
        }}
      >
        <div>
          <h2
            style={{
              fontSize: 16,
              marginBottom: 8,
              fontWeight: 500,
            }}
          >
            Security, DSGVO & Hosting in der EU.
          </h2>
          <p
            style={{
              fontSize: 13,
              color: colors.textMuted,
              maxWidth: 620,
              marginBottom: 14,
            }}
          >
            Compliance Hub ist für Industrie‑Mittelstand und Kanzleien im
            DACH‑Raum gebaut: EU‑Hosting, deutsche Server‑Optionen und ein
            Setup, das NIS2, EU AI Act, DSGVO sowie ISO‑27001/42001 abdeckt.
          </p>
          <ul
            style={{
              listStyle: 'none',
              padding: 0,
              margin: 0,
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
            }}
          >
            {bullets.map((b) => (
              <li
                key={b}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 8,
                  fontSize: 13,
                  color: colors.text,
                  lineHeight: 1.5,
                }}
              >
                <span
                  style={{
                    marginTop: 4,
                    width: 7,
                    height: 7,
                    borderRadius: '999px',
                    backgroundColor: colors.accentGreen,
                    boxShadow: '0 0 10px rgba(34,197,94,0.8)',
                    flexShrink: 0,
                  }}
                />
                <span>{b}</span>
              </li>
            ))}
          </ul>
        </div>

        <div
          style={{
            borderRadius: 18,
            border: `1px solid ${colors.border}`,
            background:
              'radial-gradient(circle at top, rgba(56,189,248,0.16), rgba(2,6,23,0.98))',
            padding: 16,
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
            fontSize: 11,
            maxWidth: 760,
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
            }}
          >
            <span style={{ color: colors.textMuted }}>Infrastruktur‑Snapshot</span>
            <span style={{ color: colors.textMuted }}> Architektur</span>
          </div>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
              gap: 10,
              marginTop: 8,
            }}
          >
            <div
              style={{
                borderRadius: 12,
                padding: 10,
                backgroundColor: colors.bgPanel,
                border: `1px solid ${colors.border}`,
              }}
            >
              <div style={{ fontSize: 11, marginBottom: 6 }}>Vercel</div>
              <div style={{ fontSize: 12, marginBottom: 2 }}>
                Frontend &amp; Edge
              </div>
              <div style={{ fontSize: 10, color: colors.textMuted }}>
                EU‑Regionen, TLS.
              </div>
            </div>
            <div
              style={{
                borderRadius: 12,
                padding: 10,
                backgroundColor: colors.bgPanel,
                border: `1px solid ${colors.border}`,
              }}
            >
              <div style={{ fontSize: 11, marginBottom: 6 }}>Postgres</div>
              <div style={{ fontSize: 12, marginBottom: 2 }}>
                Supabase / Neon
              </div>
              <div style={{ fontSize: 10, color: colors.textMuted }}>
                Postgres mit RLS.
              </div>
            </div>
            <div
              style={{
                borderRadius: 12,
                padding: 10,
                backgroundColor: colors.bgPanel,
                border: `1px solid ${colors.border}`,
              }}
            >
              <div style={{ fontSize: 11, marginBottom: 6 }}>Hetzner (DE)</div>
              <div style={{ fontSize: 12, marginBottom: 2 }}>
                Compute &amp; Storage
              </div>
              <div style={{ fontSize: 10, color: colors.textMuted }}>
                DE/EU‑Hosting.
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* Footer */

function Footer() {
  return (
    <footer
      style={{
        borderTop: `1px solid ${colors.border}`,
        padding: '14px 0 18px',
      }}
    >
      <div
        style={{
          maxWidth: layout.maxWidth,
          margin: '0 auto',
          padding: `0 ${layout.sidePadding}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: 11,
          color: colors.textMuted,
        }}
      >
        <div>
          © {new Date().getFullYear()} Compliance Hub · DACH · All rights
          reserved.
        </div>
        <div style={{ display: 'flex', gap: 14 }}>
          <a href="#" style={{ color: colors.textMuted, textDecoration: 'none' }}>
            Impressum
          </a>
          <a href="#" style={{ color: colors.textMuted, textDecoration: 'none' }}>
            Datenschutz
          </a>
        </div>
      </div>
    </footer>
  );
}

export default Page;

