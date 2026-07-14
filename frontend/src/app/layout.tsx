import type { Metadata } from "next";
import React, { Suspense } from "react";

import { DemoContextualHint } from "@/components/demo/DemoContextualHint";
import { DemoEnvironmentBanner } from "@/components/demo/DemoEnvironmentBanner";
import { DemoGuide } from "@/components/demo/DemoGuide";
import { SessionAttributionCapture } from "@/components/marketing/SessionAttributionCapture";
import { CookieBanner } from "@/components/sbs/CookieBanner";
import { SbsFooter } from "@/components/sbs/SbsFooter";
import { SbsHeader } from "@/components/sbs/SbsHeader";
import { isDemoUiDesiredForTenant } from "@/lib/workspaceDemoServer";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://complywithai.de"),
  title: "Compliance Hub · Enterprise GRC & AI Governance",
  description:
    "Mandantenfähige GRC-Plattform: EU AI Act, NIS2, ISO 42001, Board-KPIs und Exportpfade für Kanzlei-DMS – DSGVO-orientiert für den DACH-Markt. Unterstützung bei Dokumentation und Governance, keine Rechtsberatung.",
  applicationName: "Compliance Hub",
  category: "business",
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    locale: "de_DE",
    url: "/",
    siteName: "Compliance Hub",
    title: "Compliance Hub · Enterprise GRC & AI Governance",
    description:
      "Governance, Evidence und Board-Readiness für EU AI Act, NIS2 und ISO 42001.",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true, "max-image-preview": "large" },
  },
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const workspaceTenantId = await getWorkspaceTenantIdServer();
  const showDemoUi = await isDemoUiDesiredForTenant(workspaceTenantId);

  return (
    <html
      lang="de"
      className="scroll-smooth scroll-pt-[7.5rem]"
      data-scroll-behavior="smooth"
    >
      <body className="sbs-body flex min-h-screen flex-col bg-[#f5f7fb] antialiased">
        <Suspense fallback={null}>
          <SessionAttributionCapture />
        </Suspense>
        <SbsHeader />
        <DemoEnvironmentBanner visible={showDemoUi} />
        <main
          id="app-main"
          className="mx-auto w-full min-w-0 max-w-[90rem] flex-1 px-4 pb-20 pt-8 md:px-8 md:pb-24 md:pt-12"
        >
          <DemoContextualHint enabled={showDemoUi} />
          {children}
        </main>
        <DemoGuide tenantId={workspaceTenantId} enabled={showDemoUi} />
        <SbsFooter />
        <Suspense fallback={null}>
          <CookieBanner />
        </Suspense>
      </body>
    </html>
  );
}
