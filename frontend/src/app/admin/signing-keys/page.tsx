import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  CH_BADGE,
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_SECTION_LABEL,
  CH_SHELL,
} from "@/lib/boardLayout";

/** Static demo data – in production this would come from an API. */
const signingKeys = [
  {
    kid: "v1",
    fingerprint: "sha256:a1b2c3d4e5f6…",
    activeSince: "2025-06-01",
    status: "Rotiert",
    bundleCount: 142,
  },
  {
    kid: "v2",
    fingerprint: "sha256:f6e5d4c3b2a1…",
    activeSince: "2026-03-15",
    status: "Aktiv",
    bundleCount: 37,
  },
];

function daysSince(dateStr: string): number {
  const d = new Date(dateStr);
  return Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24));
}

export default function AdminSigningKeysPage() {
  const activeKey = signingKeys.find((k) => k.status === "Aktiv");
  const activeKeyAgeDays = activeKey ? daysSince(activeKey.activeSince) : 0;

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Administration"
        title="Signaturschlüssel-Verwaltung"
        description="Übersicht aller registrierten E-Signing-Schlüssel für Evidence Bundles. Schlüsselrotation gemäß GoBD/ISO 27001 Empfehlung: mindestens jährlich oder nach Sicherheitsvorfall."
        breadcrumbs={[
          { label: "Admin", href: "/admin/leads" },
          { label: "Signaturschlüssel" },
        ]}
        actions={
          <button
            type="button"
            className={`${CH_BTN_SECONDARY} text-sm`}
            title="Anleitung zur Env-Var-Aktualisierung anzeigen"
          >
            🔄 Schlüssel rotieren
          </button>
        }
      />

      {/* GoBD / eIDAS notice */}
      <section aria-label="GoBD-Hinweis" className={CH_CARD}>
        <p className={CH_SECTION_LABEL}>GoBD / eIDAS Hinweis</p>
        <p className="mt-2 text-sm text-slate-600">
          Gemäß GoBD müssen signierte Dokumente 10 Jahre nachweisbar aufbewahrt werden.
          Alle historischen Schlüssel müssen im Key-Registry verbleiben, damit Langzeit-Verifikation
          möglich bleibt. Die eIDAS-Verordnung erfordert, dass qualifizierte Signaturen auch nach
          Schlüsselrotation verifizierbar bleiben (Langzeit-Validität).
        </p>
      </section>

      {/* Active key age warning */}
      {activeKeyAgeDays > 365 && (
        <section aria-label="Schlüsselrotations-Warnung" className="rounded-2xl border border-amber-300 bg-amber-50 p-5 shadow-sm">
          <p className="text-sm font-semibold text-amber-800">
            ⚠️ Aktiver Schlüssel ist älter als 365 Tage ({activeKeyAgeDays} Tage)
          </p>
          <p className="mt-1 text-sm text-amber-700">
            GoBD und ISO 27001 empfehlen eine jährliche Schlüsselrotation. Bitte aktualisieren Sie
            den aktiven Signaturschlüssel über die Umgebungsvariable <code>TRUST_CENTER_SIGNING_KEYS</code>.
          </p>
        </section>
      )}

      {/* Key registry table */}
      <section aria-label="Registrierte Schlüssel" className={CH_CARD}>
        <p className={CH_SECTION_LABEL}>Registrierte Schlüssel</p>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs font-semibold uppercase tracking-wider text-slate-500">
                <th className="pb-3 pr-4">Key-ID</th>
                <th className="pb-3 pr-4">Fingerprint</th>
                <th className="pb-3 pr-4">Aktiv seit</th>
                <th className="pb-3 pr-4">Status</th>
                <th className="pb-3 pr-4 text-right">Signierte Bundles</th>
              </tr>
            </thead>
            <tbody>
              {signingKeys.map((key) => (
                <tr key={key.kid} className="border-b border-slate-100 last:border-0">
                  <td className="py-3 pr-4 font-mono text-sm font-medium text-slate-900">
                    {key.kid}
                  </td>
                  <td className="py-3 pr-4 font-mono text-xs text-slate-500">
                    {key.fingerprint}
                  </td>
                  <td className="py-3 pr-4 text-sm text-slate-600">
                    {key.activeSince}
                  </td>
                  <td className="py-3 pr-4">
                    {key.status === "Aktiv" ? (
                      <span className={`${CH_BADGE} bg-emerald-50 text-emerald-700 ring-emerald-200/70`}>
                        ● Aktiv
                      </span>
                    ) : (
                      <span className={`${CH_BADGE} bg-slate-100 text-slate-600 ring-slate-200/70`}>
                        ○ Rotiert
                      </span>
                    )}
                  </td>
                  <td className="py-3 pr-4 text-right text-sm font-medium text-slate-700">
                    {key.bundleCount}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Rotation instructions */}
      <section aria-label="Rotationsanleitung" className={CH_CARD}>
        <p className={CH_SECTION_LABEL}>Schlüsselrotation – Anleitung</p>
        <ol className="mt-3 list-inside list-decimal space-y-2 text-sm text-slate-600">
          <li>Neuen ECDSA-P256-Schlüssel generieren (z.B. mit OpenSSL)</li>
          <li>
            Umgebungsvariable <code className="rounded bg-slate-100 px-1 py-0.5 text-xs font-mono">TRUST_CENTER_SIGNING_KEYS</code> aktualisieren:
            neuen Key mit <code className="rounded bg-slate-100 px-1 py-0.5 text-xs font-mono">{`"active": true`}</code> hinzufügen,
            alten Key auf <code className="rounded bg-slate-100 px-1 py-0.5 text-xs font-mono">{`"active": false`}</code> setzen
          </li>
          <li>Anwendung neu starten – alle bestehenden Signaturen bleiben gültig</li>
          <li>Historische Schlüssel <strong>niemals</strong> entfernen (GoBD: 10 Jahre Aufbewahrungspflicht)</li>
        </ol>
      </section>
    </div>
  );
}
