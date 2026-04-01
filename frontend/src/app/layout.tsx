import type { Metadata } from "next";
import React from "react";

import { DemoContextualHint } from "@/components/demo/DemoContextualHint";
import { DemoEnvironmentBanner } from "@/components/demo/DemoEnvironmentBanner";
import { DemoGuide } from "@/components/demo/DemoGuide";
import { SbsFooter } from "@/components/sbs/SbsFooter";
import { SbsHeader } from "@/components/sbs/SbsHeader";
import { isDemoUiDesiredForTenant } from "@/lib/workspaceDemoServer";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

import "./globals.css";

export const metadata: Metadata = {
  title: "Compliance Hub · Enterprise GRC & AI Governance",
  description:
    "Mandantenfähige GRC-Plattform: EU AI Act, NIS2, ISO 42001, Board-KPIs und Exportpfade für Kanzlei-DMS – DSGVO-orientiert für den DACH-Markt. Unterstützung bei Dokumentation und Governance, keine Rechtsberatung.",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const workspaceTenantId = await getWorkspaceTenantIdServer();
  const showDemoUi = await isDemoUiDesiredForTenant(workspaceTenantId);

  return (
    <html lang="de" className="scroll-smooth scroll-pt-[7.5rem]">
      <body className="sbs-body flex min-h-screen flex-col bg-slate-50 antialiased">
        <SbsHeader />
        <DemoEnvironmentBanner visible={showDemoUi} />
        <main
          id="app-main"
          className="mx-auto w-full min-w-0 max-w-7xl flex-1 px-4 pb-16 pt-8 md:px-6 md:pb-20 md:pt-10"
        >
          <DemoContextualHint enabled={showDemoUi} />
          {children}
        </main>
        <DemoGuide tenantId={workspaceTenantId} enabled={showDemoUi} />
        <SbsFooter />
      </body>
    </html>
  );
}
