"use client";

import React, { useCallback, useEffect, useState } from "react";

import {
  createTenantApiKey,
  fetchTenantApiKeys,
  revokeTenantApiKey,
  type TenantApiKeyReadDto,
} from "@/lib/api";
import { CH_BTN_PRIMARY, CH_BTN_SECONDARY, CH_SECTION_LABEL } from "@/lib/boardLayout";

export function TenantApiKeysPanel({ tenantId }: { tenantId: string }) {
  const [keys, setKeys] = useState<TenantApiKeyReadDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState("ETL / Integration");
  const [lastCreatedPlain, setLastCreatedPlain] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await fetchTenantApiKeys(tenantId);
      setKeys(rows);
    } catch (e) {
      setError(
        e instanceof Error && e.message
          ? e.message
          : "API-Keys konnten nicht geladen werden.",
      );
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function onCreate() {
    setLastCreatedPlain(null);
    setError(null);
    try {
      const created = await createTenantApiKey(tenantId, newName.trim() || "API Key");
      setLastCreatedPlain(created.plain_key);
      await load();
    } catch (e) {
      setError(
        e instanceof Error && e.message
          ? e.message
          : "Neuer API-Key konnte nicht erzeugt werden.",
      );
    }
  }

  async function onRevoke(id: string) {
    if (!window.confirm("Diesen API-Key wirklich deaktivieren? Bestehende Clients verlieren den Zugriff.")) {
      return;
    }
    setBusyId(id);
    setError(null);
    try {
      await revokeTenantApiKey(tenantId, id);
      await load();
    } catch (e) {
      setError(
        e instanceof Error && e.message
          ? e.message
          : "Key konnte nicht deaktiviert werden.",
      );
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-4">
      <p className={CH_SECTION_LABEL}>API und Integrationen</p>
      <p className="text-sm text-slate-600">
        Für serverseitige Aufrufe (ERP, ETL, interne Skripte) senden Sie pro Request die Header{" "}
        <code className="rounded bg-slate-100 px-1">x-api-key</code> und{" "}
        <code className="rounded bg-slate-100 px-1">x-tenant-id</code> (Mandanten-ID wie oben).
        Den Klartext-Key nur sicher speichern; er ist nach der Erstellung nicht wieder abrufbar.
      </p>

      {error ? (
        <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-900">
          {error}
        </p>
      ) : null}

      {lastCreatedPlain ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
          <strong>Neuer Key (einmalig sichtbar):</strong>{" "}
          <span className="break-all font-mono text-xs">{lastCreatedPlain}</span>
        </div>
      ) : null}

      <div className="flex flex-wrap items-end gap-2">
        <label className="flex min-w-[12rem] flex-1 flex-col gap-1 text-xs font-medium text-slate-600">
          Bezeichnung
          <input
            className="rounded-lg border border-slate-200 px-2 py-1.5 text-sm text-slate-900"
            value={newName}
            onChange={(ev) => setNewName(ev.target.value)}
          />
        </label>
        <button type="button" className={`${CH_BTN_PRIMARY} text-sm`} onClick={() => void onCreate()}>
          Neuen Key anlegen
        </button>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-3 py-2">Name</th>
              <th className="px-3 py-2">Endung</th>
              <th className="px-3 py-2">Erstellt</th>
              <th className="px-3 py-2">Aktiv</th>
              <th className="px-3 py-2 text-right">Aktion</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-slate-500">
                  Lade API-Keys…
                </td>
              </tr>
            ) : keys.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-slate-500">
                  Keine Keys erfasst (oder noch keine mandantenspezifischen Keys – dann greift der
                  Umgebungs-API-Key).
                </td>
              </tr>
            ) : (
              keys.map((k) => (
                <tr key={k.id} className="border-b border-slate-100">
                  <td className="px-3 py-2 font-medium text-slate-900">{k.name}</td>
                  <td className="px-3 py-2 font-mono text-xs text-slate-600">…{k.key_last4}</td>
                  <td className="px-3 py-2 text-slate-600">{k.created_at}</td>
                  <td className="px-3 py-2">{k.active ? "Ja" : "Nein"}</td>
                  <td className="px-3 py-2 text-right">
                    {k.active ? (
                      <button
                        type="button"
                        className={`${CH_BTN_SECONDARY} text-xs`}
                        disabled={busyId === k.id}
                        onClick={() => void onRevoke(k.id)}
                      >
                        {busyId === k.id ? "…" : "Deaktivieren"}
                      </button>
                    ) : (
                      <span className="text-xs text-slate-400">—</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-3 text-sm text-slate-600">
        <p className="font-semibold text-slate-800">Weitere Integrationen</p>
        <p className="mt-1">
          SAP BTP / S/4HANA, DATEV-Export und DMS-Anbindungen sind für die Roadmap vorgesehen –
          <span className="font-medium text-slate-700"> Coming soon</span>.
        </p>
      </div>
    </div>
  );
}
