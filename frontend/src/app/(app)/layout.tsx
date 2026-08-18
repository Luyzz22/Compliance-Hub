import React, { Suspense } from "react";

import { DemoContextualHint } from "@/components/demo/DemoContextualHint";
import { DemoEnvironmentBanner } from "@/components/demo/DemoEnvironmentBanner";
import { DemoGuide } from "@/components/demo/DemoGuide";
import { SessionAttributionCapture } from "@/components/marketing/SessionAttributionCapture";
import { CookieBanner } from "@/components/sbs/CookieBanner";
import { SbsFooter } from "@/components/sbs/SbsFooter";
import { SbsHeader } from "@/components/sbs/SbsHeader";
import { isPublicSiteRelease } from "@/lib/releaseProfile";
import { isDemoUiDesiredForTenant } from "@/lib/workspaceDemoServer";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

/**
 * Shell für die authentifizierte Produktanwendung (Board, Workspace, Admin).
 * Die öffentliche Website nutzt bewusst eine eigene Shell in `(marketing)`.
 */
export default async function AppLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const publicSite = isPublicSiteRelease();
  const workspaceTenantId = publicSite ? "" : await getWorkspaceTenantIdServer();
  const showDemoUi = publicSite
    ? false
    : await isDemoUiDesiredForTenant(workspaceTenantId);

  return (
    <>
      {!publicSite ? (
        <Suspense fallback={null}>
          <SessionAttributionCapture />
        </Suspense>
      ) : null}
      <SbsHeader publicSite={publicSite} />
      <DemoEnvironmentBanner visible={showDemoUi} />
      <main
        id="app-main"
        className="mx-auto w-full min-w-0 max-w-[90rem] flex-1 px-4 pb-20 pt-8 md:px-8 md:pb-24 md:pt-12"
      >
        <DemoContextualHint enabled={showDemoUi} />
        {children}
      </main>
      {!publicSite ? (
        <DemoGuide tenantId={workspaceTenantId} enabled={showDemoUi} />
      ) : null}
      <SbsFooter publicSite={publicSite} />
      {!publicSite ? (
        <Suspense fallback={null}>
          <CookieBanner />
        </Suspense>
      ) : null}
    </>
  );
}
