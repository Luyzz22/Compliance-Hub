import Link from "next/link";

import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import { CH_BTN_PRIMARY, CH_CARD, CH_SHELL } from "@/lib/boardLayout";

export function LocalIdentityUnavailable({ title }: { title: string }) {
  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Unternehmensidentität"
        title={title}
        description="Lokale Konten sind im Enterprise-Produktionsprofil deaktiviert. Identität, MFA und Zugriffsrichtlinien werden zentral verwaltet."
      />
      <div className={CH_CARD}>
        <h2 className="text-lg font-semibold text-slate-950">Entra ID erforderlich</h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Bitte verwenden Sie die Unternehmensanmeldung. Registrierung, Passwortpflege und
          Wiederherstellung erfolgen durch die freigegebene Identitätsadministration; diese
          Anwendung verarbeitet dafür keine lokalen Passwörter.
        </p>
        <Link href="/auth/login" className={`${CH_BTN_PRIMARY} mt-5`}>
          Zur Unternehmensanmeldung
        </Link>
      </div>
    </div>
  );
}

export function IdentityCapabilityPending() {
  return (
    <div className={CH_SHELL}>
      <p className="py-16 text-center text-sm text-slate-600" role="status">
        Identitätsrichtlinie wird geprüft …
      </p>
    </div>
  );
}
