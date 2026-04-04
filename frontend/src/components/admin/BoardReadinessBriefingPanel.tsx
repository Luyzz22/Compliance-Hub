"use client";

import { useCallback, useState } from "react";

import { BOARD_READINESS_BRIEFING_OUTLINE_DE } from "@/lib/boardReadinessBriefingTypes";
import type { BoardReadinessBriefingPayload } from "@/lib/boardReadinessBriefingTypes";

export function BoardReadinessBriefingPanel() {
  const [briefing, setBriefing] = useState<BoardReadinessBriefingPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [baselineMsg, setBaselineMsg] = useState<string | null>(null);

  const generate = useCallback(async () => {
    setLoading(true);
    setError(null);
    setBaselineMsg(null);
    try {
      const r = await fetch("/api/admin/board-readiness/briefing", { credentials: "include" });
      if (r.status === 401) {
        setError("Nicht angemeldet (Admin-Secret).");
        setBriefing(null);
        return;
      }
      if (!r.ok) {
        setError(`HTTP ${r.status}`);
        return;
      }
      const data = (await r.json()) as { ok?: boolean; briefing?: BoardReadinessBriefingPayload };
      setBriefing(data.briefing ?? null);
    } catch {
      setError("Netzwerkfehler");
    } finally {
      setLoading(false);
    }
  }, []);

  const saveBaseline = useCallback(async () => {
    setBaselineMsg(null);
    try {
      const r = await fetch("/api/admin/board-readiness/briefing/baseline", {
        method: "POST",
        credentials: "include",
      });
      if (!r.ok) {
        setBaselineMsg(`Baseline speichern fehlgeschlagen (${r.status}).`);
        return;
      }
      const data = (await r.json()) as { message_de?: string };
      setBaselineMsg(data.message_de ?? "Gespeichert.");
    } catch {
      setBaselineMsg("Netzwerkfehler beim Speichern der Baseline.");
    }
  }, []);

  const copyMd = useCallback(async () => {
    if (!briefing?.markdown_de) return;
    try {
      await navigator.clipboard.writeText(briefing.markdown_de);
      setBaselineMsg("Markdown in die Zwischenablage kopiert.");
    } catch {
      setBaselineMsg("Kopieren nicht möglich (Browser-Berechtigung).");
    }
  }, [briefing?.markdown_de]);

  const downloadMd = useCallback(() => {
    if (!briefing?.markdown_de) return;
    const blob = new Blob([briefing.markdown_de], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `board-readiness-briefing-${briefing.generated_at.slice(0, 10)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }, [briefing]);

  return (
    <section className="rounded-xl border border-indigo-200 bg-indigo-50/40 p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-indigo-800">Wave 35</p>
          <h2 className="text-sm font-semibold text-slate-900">Board Readiness Briefing</h2>
          <p className="mt-1 max-w-3xl text-xs text-slate-600">
            Strukturiertes Memo-/Deck-Gerüst aus Live-Dashboard-Daten. Redaktion und rechtliche Prüfung
            erfolgen außerhalb der App.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void generate()}
            disabled={loading}
            className="rounded-lg bg-indigo-900 px-3 py-1.5 text-sm text-white hover:bg-indigo-800 disabled:opacity-50"
          >
            {loading ? "Erzeuge…" : "Briefing erzeugen"}
          </button>
          <button
            type="button"
            onClick={() => void saveBaseline()}
            className="rounded-lg border border-indigo-300 bg-white px-3 py-1.5 text-sm text-indigo-950 hover:bg-indigo-50"
          >
            Baseline für Deltas speichern
          </button>
        </div>
      </div>

      <details className="mt-3 rounded-lg border border-indigo-100 bg-white/70 px-3 py-2 text-xs text-slate-700">
        <summary className="cursor-pointer font-medium text-slate-800">Gliederung (Outline)</summary>
        <ul className="mt-2 list-inside list-decimal space-y-1">
          {BOARD_READINESS_BRIEFING_OUTLINE_DE.map((o) => (
            <li key={o.id}>
              <span className="font-medium">{o.title_de}</span> – {o.purpose_de}
            </li>
          ))}
        </ul>
      </details>

      {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
      {baselineMsg ? <p className="mt-2 text-sm text-indigo-900">{baselineMsg}</p> : null}

      {briefing ? (
        <div className="mt-4 space-y-4 border-t border-indigo-100 pt-4">
          <p className="font-mono text-[10px] text-slate-500">
            Briefing: {new Date(briefing.generated_at).toLocaleString("de-DE")} · Quelle Dashboard:{" "}
            {new Date(briefing.source_board_readiness_generated_at).toLocaleString("de-DE")}
            {briefing.baseline_saved_at
              ? ` · Baseline: ${new Date(briefing.baseline_saved_at).toLocaleString("de-DE")}`
              : " · Keine Baseline-Datei"}
          </p>

          {briefing.delta_bullets_de.length ? (
            <div>
              <h3 className="text-xs font-semibold text-slate-900">Delta (Kurz)</h3>
              <ul className="mt-1 list-inside list-disc text-xs text-slate-700">
                {briefing.delta_bullets_de.map((d) => (
                  <li key={d}>{d}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="space-y-3">
            {briefing.sections.map((s) => (
              <div key={s.id} className="rounded-lg border border-slate-200 bg-white p-3">
                <h3 className="text-xs font-semibold text-slate-900">{s.heading_de}</h3>
                <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-slate-800">
                  {s.bullets.map((b, i) => (
                    <li key={i} className="whitespace-pre-wrap">
                      {b}
                    </li>
                  ))}
                </ul>
                {s.references?.length ? (
                  <div className="mt-2 border-t border-slate-100 pt-2 text-[10px] text-slate-600">
                    <span className="font-medium text-slate-700">Referenzen: </span>
                    {s.references.map((r) => (
                      <span key={r.ref_id} className="mr-2 font-mono">
                        {r.ref_id}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
            ))}
          </div>

          <div>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-xs font-semibold text-slate-900">Markdown (Export)</h3>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => void copyMd()}
                  className="rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-800 hover:bg-slate-50"
                >
                  Kopieren
                </button>
                <button
                  type="button"
                  onClick={() => downloadMd()}
                  className="rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-800 hover:bg-slate-50"
                >
                  .md laden
                </button>
              </div>
            </div>
            <textarea
              readOnly
              className="mt-2 h-64 w-full resize-y rounded-lg border border-slate-200 bg-slate-50 p-2 font-mono text-[11px] text-slate-800"
              value={briefing.markdown_de}
              aria-label="Board Readiness Briefing als Markdown"
            />
          </div>
        </div>
      ) : null}
    </section>
  );
}
