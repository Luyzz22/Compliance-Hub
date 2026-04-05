"use client";

import { useCallback, useEffect, useState } from "react";

import type { MandantReadinessAdvisorPayload } from "@/lib/mandantReadinessAdvisorTypes";

type Props = { adminConfigured: boolean };

export function AdvisorMandantExportClient({ adminConfigured }: Props) {
  const [clientId, setClientId] = useState("");
  const [payload, setPayload] = useState<MandantReadinessAdvisorPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [bundleLoading, setBundleLoading] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const c = new URLSearchParams(window.location.search).get("client_id")?.trim();
    if (c) setClientId(c);
  }, []);

  const load = useCallback(async () => {
    const id = clientId.trim();
    if (!id) {
      setError("Bitte Mandanten-ID (client_id) eingeben.");
      return;
    }
    setLoading(true);
    setError(null);
    setMsg(null);
    try {
      const q = new URLSearchParams({ client_id: id });
      const r = await fetch(`/api/internal/advisor/mandant-readiness-export?${q}`, {
        credentials: "include",
      });
      if (r.status === 401) {
        setError("Nicht angemeldet (Admin-Secret).");
        setPayload(null);
        return;
      }
      if (r.status === 400) {
        const j = (await r.json()) as { detail?: string };
        setError(j.detail ?? "Ungültige Mandanten-ID.");
        setPayload(null);
        return;
      }
      if (!r.ok) {
        setError(`HTTP ${r.status}`);
        setPayload(null);
        return;
      }
      const data = (await r.json()) as {
        ok?: boolean;
        mandant_readiness_export?: MandantReadinessAdvisorPayload;
      };
      setPayload(data.mandant_readiness_export ?? null);
    } catch {
      setError("Netzwerkfehler");
    } finally {
      setLoading(false);
    }
  }, [clientId]);

  const copyMd = useCallback(async () => {
    if (!payload?.markdown_de) return;
    try {
      await navigator.clipboard.writeText(payload.markdown_de);
      setMsg("Markdown kopiert.");
    } catch {
      setMsg("Kopieren fehlgeschlagen.");
    }
  }, [payload?.markdown_de]);

  const downloadMd = useCallback(() => {
    if (!payload?.markdown_de) return;
    const blob = new Blob([payload.markdown_de], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `mandant-readiness-${payload.kompakt.mandant_id}-${payload.meta.generated_at.slice(0, 10)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }, [payload]);

  const downloadDatevBundle = useCallback(async () => {
    const id = clientId.trim();
    if (!id) {
      setError("Bitte Mandanten-ID (client_id) eingeben.");
      return;
    }
    setBundleLoading(true);
    setError(null);
    setMsg(null);
    try {
      const q = new URLSearchParams({ client_id: id });
      const r = await fetch(`/api/internal/advisor/datev-export-bundle?${q}`, {
        credentials: "include",
      });
      if (r.status === 401) {
        setError("Nicht angemeldet (Admin-Secret).");
        return;
      }
      if (r.status === 400) {
        const j = (await r.json()) as { detail?: string };
        setError(j.detail ?? "Ungültige Mandanten-ID.");
        return;
      }
      if (!r.ok) {
        setError(`HTTP ${r.status}`);
        return;
      }
      const blob = await r.blob();
      const cd = r.headers.get("Content-Disposition");
      const match = cd?.match(/filename="([^"]+)"/);
      const name = match?.[1] ?? `datev-kanzlei-bundle-${id}.zip`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      a.click();
      URL.revokeObjectURL(url);
      setMsg("ZIP-Arbeitspaket geladen.");
    } catch {
      setError("Netzwerkfehler");
    } finally {
      setBundleLoading(false);
    }
  }, [clientId]);

  if (!adminConfigured) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-900">
        Nicht konfiguriert (<code className="font-mono">LEAD_ADMIN_SECRET</code>).
      </div>
    );
  }

  return (
    <div className="space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Wave 37 · Kanzlei / Berater</p>
        <h1 className="text-xl font-semibold text-slate-900">Mandanten-Readiness-Export</h1>
        <p className="mt-2 text-sm text-slate-600">
          Kompakter Status für Steuerberater, WP und GRC-Berater – ein Mandant pro Export. Nutzt dieselben
          API-Signale wie das Board-Readiness-Dashboard, aber mandantenzentriert und ohne Board-Pack-Ton.
        </p>
        <p className="mt-2 text-xs text-slate-500">
          API:{" "}
          <code className="rounded bg-slate-100 px-1 text-[11px]">
            GET /api/internal/advisor/mandant-readiness-export?client_id=…
          </code>
          <br />
          ZIP (Wave 38):{" "}
          <code className="rounded bg-slate-100 px-1 text-[11px]">
            GET /api/internal/advisor/datev-export-bundle?client_id=…
          </code>
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-2">
        <label className="block text-xs font-medium text-slate-700" htmlFor="mandant-id">
          Mandanten-ID (client_id)
        </label>
        <input
          id="mandant-id"
          className="min-w-[240px] flex-1 rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm"
          placeholder="z. B. tenant-acme-001"
          value={clientId}
          onChange={(e) => setClientId(e.target.value)}
        />
        <button
          type="button"
          disabled={loading}
          onClick={() => void load()}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {loading ? "Lade…" : "Export erzeugen"}
        </button>
        <button
          type="button"
          disabled={bundleLoading}
          onClick={() => void downloadDatevBundle()}
          className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm text-slate-900 hover:bg-slate-50 disabled:opacity-50"
        >
          {bundleLoading ? "ZIP…" : "DATEV-/Kanzlei-Export erstellen"}
        </button>
      </div>

      <p className="text-xs text-slate-500">
        <a className="text-cyan-700 underline" href="/admin/advisor-portfolio">
          Kanzlei-Cockpit
        </a>
        {" · "}
        <a className="text-cyan-700 underline" href="/admin/board-readiness">
          Board Readiness
        </a>
      </p>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      {msg ? <p className="text-sm text-emerald-800">{msg}</p> : null}

      {payload ? (
        <div className="space-y-4 border-t border-slate-100 pt-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">1. Mandantenstatus</h2>
            <p className="mt-1 text-sm text-slate-800">{payload.kompakt.readiness_kurzfassung_de}</p>
            <ul className="mt-2 list-inside list-disc text-xs text-slate-700">
              <li>Bezeichnung: {payload.kompakt.mandanten_bezeichnung}</li>
              <li>KI-Systeme: {payload.kompakt.ki_systeme_gesamt} · Hochrisiko: {payload.kompakt.ki_hochrisiko_anzahl}</li>
              <li>Reife-Orientierung: {payload.kompakt.governance_reifeklasse_de}</li>
              <li>Ansprechpartner: {payload.kompakt.ansprechpartner_hinweis_de}</li>
            </ul>
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-900">2. Offene Prüfpunkte</h2>
            <ul className="mt-2 space-y-1 text-xs text-slate-800">
              {payload.offene_punkte.length ? (
                payload.offene_punkte.map((o) => (
                  <li key={o.referenz_id + o.pruefpunkt_de.slice(0, 20)}>
                    <span className="font-mono text-violet-800">{o.referenz_id}</span> · {o.pruefpunkt_de}
                  </li>
                ))
              ) : (
                <li>Keine automatisch erkannten offenen Punkte.</li>
              )}
            </ul>
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-900">3. Nächste Schritte</h2>
            <ul className="mt-2 list-inside list-disc text-xs text-slate-800">
              {payload.naechste_schritte.map((s, i) => (
                <li key={i}>
                  <strong>{s.fuer}:</strong> {s.schritt_de}
                </li>
              ))}
            </ul>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => void copyMd()}
              className="rounded border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-800"
            >
              Markdown kopieren
            </button>
            <button
              type="button"
              onClick={() => downloadMd()}
              className="rounded border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-800"
            >
              .md laden
            </button>
          </div>
          <textarea
            readOnly
            className="h-56 w-full resize-y rounded-lg border border-slate-200 bg-slate-50 p-2 font-mono text-[11px]"
            value={payload.markdown_de}
            aria-label="Mandanten-Readiness Markdown"
          />
        </div>
      ) : null}
    </div>
  );
}
