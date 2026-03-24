import type { Metadata } from "next";
import React from "react";

import { SbsFooter } from "@/components/sbs/SbsFooter";
import { SbsHeader } from "@/components/sbs/SbsHeader";

import "./globals.css";

export const metadata: Metadata = {
  title: "Compliance Hub · Enterprise GRC & AI Governance",
  description:
    "Mandantenfähige GRC-Plattform: EU AI Act, NIS2, ISO 42001, Board-KPIs und DATEV-ready Exporte – DSGVO-orientiert für den DACH-Markt.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="de">
      <body className="has-fixed-header sbs-body flex min-h-screen flex-col bg-slate-100/80">
        <SbsHeader />
        <main
          id="app-main"
          className="mx-auto w-full min-w-0 max-w-7xl flex-1 px-4 py-8 pb-16 md:px-6 md:py-10"
        >
          {children}
        </main>
        <SbsFooter />
      </body>
    </html>
  );
}
