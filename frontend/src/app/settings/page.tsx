import Link from "next/link";
import React from "react";

import { DemoTenantSetupPanel } from "@/components/demo/DemoTenantSetupPanel";
import { TenantApiKeysPanel } from "@/components/settings/TenantApiKeysPanel";
import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import { TenantUsageSummary } from "@/components/usage/TenantUsageSummary";
import {
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_SECTION_LABEL,
  CH_SHELL,
} from "@/lib/boardLayout";
import { featureApiKeysUi, featureDemoSeeding } from "@/lib/config";

const TENANT_ID =
  process.env.NEXT_PUBLIC_TENANT_ID ||
  process.env.COMPLIANCEHUB_TENANT_ID ||
  "tenant-overview-001";

export default function SettingsPage() {
  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        title="Einstellungen"
        description="Mandanten-Stammdaten, API-Zugriff und Integrations-Platzhalter – ohne Änderung an Backend-Verträgen."
      />

      <section className="grid gap-4 md:grid-cols-2">
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Mandant</p>
          <p className="mt-2 font-mono text-sm font-semibold text-slate-900">{TENANT_ID}</p>
          <p className="mt-2 text-sm text-slate-600">
            Anzeigename, Rechtsform und Kontakte werden produktiv über die Admin-API gepflegt.
          </p>
          <Link
            href="/tenant/compliance-overview"
            className={`${CH_BTN_SECONDARY} mt-4 inline-flex text-xs`}
          >
            Zur Compliance-Übersicht
          </Link>
        </article>

        {featureApiKeysUi() ? (
          <article className={`${CH_CARD} md:col-span-2`}>
            <TenantApiKeysPanel tenantId={TENANT_ID} />
          </article>
        ) : (
          <article className={CH_CARD}>
            <p className={CH_SECTION_LABEL}>API-Keys</p>
            <p className="mt-2 text-sm text-slate-600">
              API-Key-UI ist in dieser Umgebung deaktiviert (NEXT_PUBLIC_FEATURE_API_KEYS_UI).
            </p>
            <p className="mt-3 text-xs text-slate-500">
              Setzen Sie <code className="rounded bg-slate-100 px-1">COMPLIANCEHUB_API_KEY</code>{" "}
              serverseitig; im Browser nur{" "}
              <code className="rounded bg-slate-100 px-1">NEXT_PUBLIC_*</code> für Demo-Umgebungen.
            </p>
          </article>
        )}

        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Benutzer & Rollen</p>
          <p className="mt-2 text-sm text-slate-600">
            SSO (Azure AD, SAP IAS) und rollenbasierte Workspace-Zugriffe – Platzhalter für
            Enterprise-Onboarding.
          </p>
          <Link
            href="/auth/profile"
            className={`${CH_BTN_SECONDARY} mt-4 inline-flex text-xs`}
          >
            Benutzerprofil verwalten
          </Link>
        </article>

        {featureDemoSeeding() ? (
          <article className={`${CH_CARD} md:col-span-2`}>
            <DemoTenantSetupPanel defaultTenantId={TENANT_ID} />
          </article>
        ) : null}

        <div className="md:col-span-2">
          <TenantUsageSummary mode="tenant" tenantId={TENANT_ID} />
        </div>

      </section>
    </div>
  );
}
