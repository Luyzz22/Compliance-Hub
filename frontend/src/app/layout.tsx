import type { Metadata } from "next";
import { connection } from "next/server";
import React from "react";

import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://complywithai.de"),
  title: {
    default: "Compliance Hub · Governance-Layer für AI, Security und Compliance",
    template: "%s · Compliance Hub",
  },
  description:
    "Compliance Hub verbindet KI-Register, Controls, Evidenzen und Board-Reporting in einer mandantenfähigen Governance-Plattform für EU AI Act, ISO 42001, ISO 27001, NIS2 und DSGVO im DACH-Raum.",
  applicationName: "Compliance Hub",
  category: "business",
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    locale: "de_DE",
    url: "/",
    siteName: "Compliance Hub",
    title: "Compliance Hub · Governance-Layer für AI, Security und Compliance",
    description:
      "Map once, comply many: ein Kontrollmodell für EU AI Act, ISO 42001, ISO 27001/27701, NIS2 und DSGVO.",
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
  await connection();

  return (
    <html
      lang="de"
      className="scroll-smooth scroll-pt-[7.5rem]"
      data-scroll-behavior="smooth"
    >
      <body className="sbs-body flex min-h-screen flex-col bg-[#f6f8fa] antialiased">
        {children}
      </body>
    </html>
  );
}
