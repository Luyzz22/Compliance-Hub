/** Informationsarchitektur der öffentlichen Website (Single Source für Header, Footer, Sitemap). */

export const MARKETING_ROUTES = {
  home: "/",
  platform: "/plattform",
  aiAct: "/eu-ai-act-iso-42001",
  nis2: "/nis2-kritis",
  advisors: "/fuer-beratungen",
  integrations: "/integrationen",
  security: "/sicherheit",
  resources: "/ressourcen",
  productTour: "/produkt-tour",
  demo: "/demo",
  contact: "/kontakt",
  trustCenter: "/trust-center",
  imprint: "/impressum",
  privacy: "/datenschutz",
  terms: "/agb",
} as const;

export type MarketingNavItem = {
  label: string;
  href: string;
  description?: string;
};

export type MarketingNavGroup = {
  id: string;
  label: string;
  href?: string;
  /** Ohne `items` rendert der Header einen direkten Link. */
  items?: MarketingNavItem[];
  footnote?: string;
};

export const MARKETING_NAV: readonly MarketingNavGroup[] = [
  {
    id: "plattform",
    label: "Plattform",
    href: MARKETING_ROUTES.platform,
    items: [
      {
        label: "Plattform-Überblick",
        href: MARKETING_ROUTES.platform,
        description: "Inventar, Controls, Evidenz, Risiko und Board-Output in einem Modell",
      },
      {
        label: "Control Mapping",
        href: `${MARKETING_ROUTES.platform}#control-mapping`,
        description: "Ein Control einmal pflegen, über mehrere Regime nachweisen",
      },
      {
        label: "Evidence Engine",
        href: `${MARKETING_ROUTES.platform}#evidence`,
        description: "Nachweise mit Herkunft, Version und Review-Zyklus",
      },
      {
        label: "Board Reporting",
        href: `${MARKETING_ROUTES.platform}#board-reporting`,
        description: "Lage, Entscheidungsbedarf und Fristen in Board-Sprache",
      },
      {
        label: "Produkt-Tour",
        href: MARKETING_ROUTES.productTour,
        description: "Fünf Minuten durch den Governance-Ablauf",
      },
    ],
    footnote: "Alle Ansichten sind illustrativ und zeigen keine Kundendaten.",
  },
  {
    id: "loesungen",
    label: "Lösungen",
    items: [
      {
        label: "EU AI Act & ISO 42001",
        href: MARKETING_ROUTES.aiAct,
        description: "Klassifizierung, Anforderungen, AIMS-Cross-Mapping",
      },
      {
        label: "NIS2 & KRITIS",
        href: MARKETING_ROUTES.nis2,
        description: "Risiko- und Maßnahmenmanagement nach Art. 21",
      },
      {
        label: "Industrie & Mittelstand",
        href: `${MARKETING_ROUTES.platform}#industrie`,
        description: "Governance nahe an ERP-, Fertigungs- und IT-Prozessen",
      },
      {
        label: "ISO 27001 & DSGVO",
        href: `${MARKETING_ROUTES.platform}#regelwerke`,
        description: "Bestehendes ISMS und Datenschutz mit einbeziehen",
      },
    ],
  },
  {
    id: "beratungen",
    label: "Für Beratungen",
    href: MARKETING_ROUTES.advisors,
  },
  {
    id: "integrationen",
    label: "Integrationen",
    href: MARKETING_ROUTES.integrations,
  },
  {
    id: "sicherheit",
    label: "Sicherheit",
    href: MARKETING_ROUTES.security,
  },
  {
    id: "ressourcen",
    label: "Ressourcen",
    href: MARKETING_ROUTES.resources,
  },
  {
    id: "unternehmen",
    label: "Unternehmen",
    items: [
      {
        label: "Trust Center",
        href: MARKETING_ROUTES.trustCenter,
        description: "Sicherheits- und Datenschutzangaben im Überblick",
      },
      {
        label: "Kontakt",
        href: MARKETING_ROUTES.contact,
        description: "Direkter Draht zu Produkt und Delivery",
      },
      {
        label: "Impressum",
        href: MARKETING_ROUTES.imprint,
      },
      {
        label: "Datenschutz",
        href: MARKETING_ROUTES.privacy,
      },
    ],
  },
];

export const FOOTER_COLUMNS: readonly {
  title: string;
  items: MarketingNavItem[];
}[] = [
  {
    title: "Plattform",
    items: [
      { label: "Plattform-Überblick", href: MARKETING_ROUTES.platform },
      { label: "Control Mapping", href: `${MARKETING_ROUTES.platform}#control-mapping` },
      { label: "Evidence Engine", href: `${MARKETING_ROUTES.platform}#evidence` },
      { label: "Board Reporting", href: `${MARKETING_ROUTES.platform}#board-reporting` },
      { label: "Produkt-Tour", href: MARKETING_ROUTES.productTour },
    ],
  },
  {
    title: "Lösungen",
    items: [
      { label: "EU AI Act & ISO 42001", href: MARKETING_ROUTES.aiAct },
      { label: "NIS2 & KRITIS", href: MARKETING_ROUTES.nis2 },
      { label: "Für Kanzleien & Beratungen", href: MARKETING_ROUTES.advisors },
      { label: "Integrationen", href: MARKETING_ROUTES.integrations },
    ],
  },
  {
    title: "Ressourcen",
    items: [
      { label: "Compliance Briefing", href: MARKETING_ROUTES.resources },
      { label: "EU AI Act Readiness Guide", href: `${MARKETING_ROUTES.resources}#eu-ai-act-readiness-guide` },
      { label: "NIS2 Management-Checkliste", href: `${MARKETING_ROUTES.resources}#nis2-management-checkliste` },
      { label: "Board-Report-Vorlage", href: `${MARKETING_ROUTES.resources}#board-report-vorlage` },
    ],
  },
  {
    title: "Sicherheit",
    items: [
      { label: "Sicherheit & Architektur", href: MARKETING_ROUTES.security },
      { label: "Trust Center", href: MARKETING_ROUTES.trustCenter },
      { label: "Mandantenisolation", href: `${MARKETING_ROUTES.security}#mandantenisolation` },
      { label: "Hosting in der EU", href: `${MARKETING_ROUTES.security}#hosting` },
    ],
  },
  {
    title: "Unternehmen",
    items: [
      { label: "Demo anfragen", href: MARKETING_ROUTES.demo },
      { label: "Kontakt", href: MARKETING_ROUTES.contact },
      { label: "Impressum", href: MARKETING_ROUTES.imprint },
      { label: "Datenschutz", href: MARKETING_ROUTES.privacy },
    ],
  },
];
