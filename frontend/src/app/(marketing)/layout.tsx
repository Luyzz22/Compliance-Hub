import React, { Suspense } from "react";

import { AnnouncementBar } from "@/components/marketing/AnnouncementBar";
import { MarketingFooter } from "@/components/marketing/MarketingFooter";
import { MarketingHeader } from "@/components/marketing/MarketingHeader";
import { SessionAttributionCapture } from "@/components/marketing/SessionAttributionCapture";
import { CookieBanner } from "@/components/sbs/CookieBanner";
import { isPublicSiteRelease } from "@/lib/releaseProfile";

/**
 * Shell der öffentlichen Website. Vollbreite Sektionen, eigene Navigation und
 * ein Footer, der die rechtlichen Hinweise trägt.
 */
export default function MarketingLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const publicSite = isPublicSiteRelease();

  return (
    <div className="mk-scope flex min-h-screen flex-col bg-white">
      <a href="#marketing-main" className="mk-skip-link">
        Zum Inhalt springen
      </a>
      {!publicSite ? (
        <Suspense fallback={null}>
          <SessionAttributionCapture />
        </Suspense>
      ) : null}
      <AnnouncementBar />
      <MarketingHeader showLogin={!publicSite} />
      <main id="marketing-main" className="min-w-0 flex-1">
        {children}
      </main>
      <MarketingFooter />
      {!publicSite ? (
        <Suspense fallback={null}>
          <CookieBanner />
        </Suspense>
      ) : null}
    </div>
  );
}
