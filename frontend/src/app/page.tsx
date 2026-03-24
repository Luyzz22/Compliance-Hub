import Link from "next/link";
import React from "react";

export default function HomePage() {
  return (
    <>
      <section className="hero-2026">
        <div className="hero-content animate-in">
          <div className="hero-badge">
            <span className="pulse-dot" aria-hidden />
            Compliance Hub · Live
          </div>
          <h1>
            Enterprise-Governance für den
            <br />
            <span className="text-gradient">deutschen Mittelstand</span>
          </h1>
          <p className="hero-subtitle">
            Von KI-System-Register und EU-AI-Act-Readiness bis zu NIS2-Board-KPIs
            und exportfähigen Nachweisen – eine Plattform für Beratungen,
            Konzerne und WP-Kanzleien. DSGVO-orientiert. Made for DACH.
          </p>
          <div className="hero-cta-group">
            <Link href="/tenant/compliance-overview" className="cta-primary">
              Tenant öffnen →
            </Link>
            <Link href="/board/kpis" className="cta-secondary">
              Board-KPIs ansehen
            </Link>
          </div>
          <div className="hero-stats">
            <div className="hero-stat">
              <div className="stat-value">4+</div>
              <div className="stat-label">Regulatory Pillars</div>
            </div>
            <div className="hero-stat">
              <div className="stat-value">RLS</div>
              <div className="stat-label">Tenant-Isolation</div>
            </div>
            <div className="hero-stat">
              <div className="stat-value">JSON</div>
              <div className="stat-label">DATEV-ready Export</div>
            </div>
            <div className="hero-stat">
              <div className="stat-value">🇩🇪</div>
              <div className="stat-label">DACH-Fokus</div>
            </div>
          </div>
        </div>
      </section>

      <section className="section-2026" style={{ padding: "40px 24px" }}>
        <div className="section-inner">
          <div
            className="trust-badges-2026"
            style={{ justifyContent: "center" }}
          >
            <div className="trust-badge-2026">
              <span className="badge-icon">🏢</span> Enterprise-Grade
            </div>
            <div className="trust-badge-2026">
              <span className="badge-icon">🔒</span> DSGVO-orientiert
            </div>
            <div className="trust-badge-2026">
              <span className="badge-icon">📋</span> EU AI Act &amp; ISO 42001
            </div>
            <div className="trust-badge-2026">
              <span className="badge-icon">⚡</span> NIS2 / KRITIS KPIs
            </div>
            <div className="trust-badge-2026">
              <span className="badge-icon">🔗</span> DATEV &amp; SAP-ready
            </div>
          </div>
        </div>
      </section>

      <section className="section-2026 alt-bg">
        <div className="section-inner">
          <div className="featured-product-2026">
            <div className="fp-grid">
              <div>
                <div className="fp-badge">🚀 Board-ready</div>
                <h2
                  style={{
                    fontSize: "clamp(1.6rem,3vw,2.4rem)",
                    fontWeight: 800,
                    letterSpacing: "-0.02em",
                    marginBottom: "16px",
                  }}
                >
                  AI Governance &amp; NIS2 in einer Ansicht
                </h2>
                <p
                  style={{
                    fontSize: "1.05rem",
                    color: "var(--sbs-text-secondary)",
                    lineHeight: 1.6,
                    marginBottom: "24px",
                  }}
                >
                  KPI-Drilldowns, Alerts mit Schwellen-Kontext, EU-AI-Act-Readiness
                  mit Maßnahmen-Deep-Links und revisionssichere Exporte – gebaut für
                  Aufsicht, ISB und externe Prüfer.
                </p>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "12px",
                    marginBottom: "28px",
                  }}
                >
                  {[
                    "KI-System-Register mit Risiko & Technical-File-Spuren",
                    "NIS2/KRITIS-Incident- und Supplier-Drilldowns",
                    "Readiness-API mit Verknüpfung zu Governance-Actions",
                    "KPI-Export JSON/CSV mit regulatory_scope für DMS/DATEV-Pipelines",
                  ].map((t) => (
                    <div
                      key={t}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                        fontSize: "0.92rem",
                        color: "var(--sbs-text-secondary)",
                      }}
                    >
                      <span style={{ color: "var(--sbs-text-accent)" }}>✓</span>
                      {t}
                    </div>
                  ))}
                </div>
                <Link href="/board/kpis" className="sbs-btn-primary">
                  Zum Board →
                </Link>
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <div
                  style={{
                    background: "#F1F5F9",
                    border: "1px solid var(--sbs-border)",
                    borderRadius: "16px",
                    padding: "32px",
                    textAlign: "center",
                    width: "100%",
                  }}
                >
                  <div style={{ fontSize: "4rem", marginBottom: "16px" }} aria-hidden>
                    📊
                  </div>
                  <div
                    style={{
                      fontSize: "0.82rem",
                      color: "#64748B",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                      marginBottom: "8px",
                    }}
                  >
                    Datenfluss
                  </div>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "center",
                      alignItems: "center",
                      gap: "12px",
                      flexWrap: "wrap",
                    }}
                  >
                    {["Register", "Policies", "Engine", "Reports"].map((x, i) => (
                      <React.Fragment key={x}>
                        {i > 0 ? (
                          <span style={{ color: "var(--sbs-text-muted)" }}>→</span>
                        ) : null}
                        <span
                          style={{
                            padding: "8px 14px",
                            background: "rgba(0,102,179,0.08)",
                            border: "1px solid rgba(0,102,179,0.2)",
                            borderRadius: "8px",
                            fontSize: "0.82rem",
                            color: "var(--sbs-text-accent)",
                          }}
                        >
                          {x}
                        </span>
                      </React.Fragment>
                    ))}
                  </div>
                  <p
                    style={{
                      fontSize: "0.82rem",
                      color: "#64748B",
                      marginTop: "16px",
                    }}
                  >
                    Ein konsistenter Pfad von Inventar bis Board-Export
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section-2026">
        <div className="section-inner">
          <div className="section-header-center">
            <div className="section-badge">Module</div>
            <h2 className="section-title">
              Board, Tenant &amp; Export.
              <br />
              Eine Oberfläche.
            </h2>
            <p className="section-subtitle">
              Wählen Sie den Einstieg: operatives Tenant-Cockpit, Vorstands-KPIs
              oder tiefe NIS2-/Readiness-Drilldowns.
            </p>
          </div>
          <div className="card-grid-3" style={{ marginBottom: "20px" }}>
            <Link href="/board/kpis" className="product-card-2026">
              <span className="arrow">→</span>
              <div className="product-icon">📈</div>
              <h3>Board KPIs</h3>
              <p>
                ISO-42001-Reife, NIS2-Incident- und Supplier-Ratios, Alerts mit
                Kennzahlen-Kontext und Exporte für CISO/Vorstand.
              </p>
              <div className="product-tags">
                <span className="tag">ISO 42001</span>
                <span className="tag">NIS2</span>
                <span className="tag">Alerts</span>
              </div>
            </Link>
            <Link href="/board/nis2-kritis" className="product-card-2026">
              <span className="arrow">→</span>
              <div className="product-icon">🛡️</div>
              <h3>NIS2 / KRITIS Drilldown</h3>
              <p>
                KPI-Typen Incident, Supplier, OT/IT – sortiert und für
                Aufsichtsreporting aufbereitet.
              </p>
              <div className="product-tags">
                <span className="tag">KRITIS</span>
                <span className="tag">OT/IT</span>
                <span className="tag">Top-N</span>
              </div>
            </Link>
            <Link href="/board/eu-ai-act-readiness" className="product-card-2026">
              <span className="arrow">→</span>
              <div className="product-icon">⚖️</div>
              <h3>EU AI Act Readiness</h3>
              <p>
                Stichtag High-Risk, kritische Anforderungen, Deep-Links zu
                Systemen und Governance-Actions.
              </p>
              <div className="product-tags">
                <span className="tag">Art. 9–15</span>
                <span className="tag">Actions</span>
                <span className="tag">Gaps</span>
              </div>
            </Link>
          </div>
          <div className="card-grid-2">
            <Link href="/tenant/compliance-overview" className="product-card-2026">
              <span className="arrow">→</span>
              <div className="product-icon">🏢</div>
              <h3>Tenant Compliance</h3>
              <p>
                AI-Systeme, Violations und Status in einem Cockpit für
                Betriebsteams.
              </p>
              <div className="product-tags">
                <span className="tag">Multi-Tenant</span>
                <span className="tag">Violations</span>
              </div>
            </Link>
            <Link
              href="/board/kpis"
              className="product-card-2026"
              style={{ borderColor: "var(--sbs-border-amber)" }}
            >
              <span className="arrow">→</span>
              <div
                className="product-icon"
                style={{ background: "var(--sbs-gradient-amber)" }}
              >
                📦
              </div>
              <h3>WP / DMS / DATEV Export</h3>
              <p>
                Strukturierte KPI-Exports mit Norm-Kontext im Envelope – bereit
                für Kanzlei- und Archiv-Workflows.
              </p>
              <div className="product-tags">
                <span className="tag">JSON</span>
                <span className="tag">CSV</span>
                <span className="tag">Audit</span>
              </div>
            </Link>
          </div>
        </div>
      </section>

      <section className="section-2026 alt-bg">
        <div className="section-inner">
          <div className="section-header-center">
            <div className="section-badge">Vorteile</div>
            <h2 className="section-title">Warum Compliance Hub</h2>
            <p className="section-subtitle">
              Normen übersetzen sich in messbare Controls – ohne Medienbrüche
              zwischen Fachbereich, IT und Prüfern.
            </p>
          </div>
          <div className="card-grid-3">
            <div className="card-2026">
              <div className="card-icon">🇩🇪</div>
              <h3>DACH &amp; Regulatorik</h3>
              <p>
                EU AI Act, NIS2, ISO 42001, DSGVO/GoBD als Leitplanken – nicht
                nur als Buzzwords, sondern im Datenmodell verankert.
              </p>
            </div>
            <div className="card-2026">
              <div className="card-icon">⚡</div>
              <h3>Board-tauglich</h3>
              <p>
                Aggregierte KPIs, Ampeln und Exporte, die ISB und Aufsicht
                direkt weiterverwenden können.
              </p>
            </div>
            <div className="card-2026">
              <div className="card-icon">🔗</div>
              <h3>Integration</h3>
              <p>
                APIs, Webhooks und Export-Jobs – andockbar an SAP, DATEV, DMS
                und n8n-Workflows.
              </p>
            </div>
            <div className="card-2026">
              <div className="card-icon">🔒</div>
              <h3>Security by design</h3>
              <p>
                Mandanten-Isolation, nachvollziehbare Audit-Events und klare
                Grenzen zwischen Demo und Produktion.
              </p>
            </div>
            <div className="card-2026">
              <div className="card-icon">📊</div>
              <h3>Evidence</h3>
              <p>
                Lücken, Maßnahmen und Reports aus einer Quelle – weniger
                Copy-Paste vor der Prüfung.
              </p>
            </div>
            <div className="card-2026">
              <div className="card-icon">🎯</div>
              <h3>Berater-first</h3>
              <p>
                Wiederholbare Blueprints und mandantenfähige Sichten für
                skalierbare GRC-Projekte.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="section-2026 alt-bg" style={{ padding: "60px 24px" }}>
        <div className="section-inner">
          <div className="section-header-center" style={{ marginBottom: "32px" }}>
            <div className="section-badge">Technologie</div>
            <h2 style={{ fontSize: "1.4rem", fontWeight: 700 }}>
              Powered by moderner Stack
            </h2>
          </div>
          <div className="tech-badges-2026">
            {[
              "FastAPI",
              "Python 3.11+",
              "Next.js",
              "PostgreSQL / RLS",
              "Pydantic v2",
              "n8n",
              "LangChain",
              "DATEV",
              "SAP S/4HANA",
              "Multi-LLM",
            ].map((t) => (
              <span key={t} className="tech-badge-2026">
                {t}
              </span>
            ))}
          </div>
        </div>
      </section>

      <section className="cta-section-2026">
        <div className="cta-box">
          <div className="section-badge" style={{ marginBottom: "20px" }}>
            Jetzt starten
          </div>
          <h2
            style={{
              fontSize: "clamp(1.6rem,3vw,2.2rem)",
              fontWeight: 800,
              letterSpacing: "-0.02em",
              marginBottom: "14px",
            }}
          >
            Bereit für Enterprise-Governance?
          </h2>
          <p
            style={{
              fontSize: "1rem",
              color: "var(--sbs-text-secondary)",
              maxWidth: "480px",
              margin: "0 auto 28px",
              lineHeight: 1.6,
            }}
          >
            Öffnen Sie das Tenant-Cockpit oder die Board-Ansicht – ohne
            Kreditkarte, rein demonstrativ gegen die ComplianceHub-API.
          </p>
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              justifyContent: "center",
              gap: "14px",
            }}
          >
            <Link
              href="/tenant/compliance-overview"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "14px 28px",
                background: "var(--sbs-gradient-amber)",
                color: "#003366",
                fontWeight: 700,
                fontSize: "0.95rem",
                borderRadius: "10px",
                textDecoration: "none",
                boxShadow: "var(--sbs-shadow-amber)",
              }}
            >
              Tenant öffnen →
            </Link>
            <Link href="/board/kpis" className="sbs-btn-secondary">
              Board-KPIs
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
