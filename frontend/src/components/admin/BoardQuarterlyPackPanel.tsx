"use client";

import { useCallback, useState } from "react";

import type { BoardPackPayload } from "@/lib/boardPackTypes";
import { BOARD_PACK_HORIZON_LABEL_DE } from "@/lib/boardPackTypes";

const PILLAR_LABEL: Record<string, string> = {
  eu_ai_act: "EU AI Act",
  iso_42001: "ISO 42001",
  nis2: "NIS2 / KRITIS",
  dsgvo: "DSGVO",
  portfolio: "Portfolio / GTM",
};

export function BoardQuarterlyPackPanel() {
  const [pack, setPack] = useState<BoardPackPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const generate = useCallback(async () => {
    setLoading(true);
    setError(null);
    setMsg(null);
    try {
      const r = await fetch("/api/admin/board-readiness/board-pack", { credentials: "include" });
      if (r.status === 401) {
        setError("Nicht angemeldet (Admin-Secret).");
        setPack(null);
        return;
      }
      if (!r.ok) {
        setError(`HTTP ${r.status}`);
        return;
      }
      const data = (await r.json()) as { ok?: boolean; board_pack?: BoardPackPayload };
      setPack(data.board_pack ?? null);
    } catch {
      setError("Netzwerkfehler");
    } finally {
      setLoading(false);
    }
  }, []);

  const copyMd = useCallback(async () => {
    if (!pack?.markdown_de) return;
    try {
      await navigator.clipboard.writeText(pack.markdown_de);
      setMsg("Markdown in die Zwischenablage kopiert.");
    } catch {
      setMsg("Kopieren nicht möglich (Browser-Berechtigung).");
    }
  }, [pack?.markdown_de]);

  const downloadMd = useCallback(() => {
    if (!pack?.markdown_de) return;
    const blob = new Blob([pack.markdown_de], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `quarterly-board-pack-${pack.meta.generated_at.slice(0, 10)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }, [pack]);

  return (
    <section className="rounded-xl border border-violet-200 bg-violet-50/40 p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-violet-900">Wave 36</p>
          <h2 className="text-sm font-semibold text-slate-900">Quarterly Board Pack</h2>
          <p className="mt-1 max-w-3xl text-xs text-slate-600">
            Formales Memo-Gerüst, priorisierte Attention-Liste und Aktionsregister – für Notion, Confluence
            oder E-Mail. Vor Versand an Board/Advisory redaktionell prüfen.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void generate()}
          disabled={loading}
          className="rounded-lg bg-violet-900 px-3 py-1.5 text-sm text-white hover:bg-violet-800 disabled:opacity-50"
        >
          {loading ? "Erzeuge…" : "Board Pack erzeugen"}
        </button>
      </div>

      {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
      {msg ? <p className="mt-2 text-sm text-violet-900">{msg}</p> : null}

      {pack ? (
        <div className="mt-4 space-y-4 border-t border-violet-100 pt-4">
          <p className="font-mono text-[10px] text-slate-500">
            {pack.version} · {new Date(pack.meta.generated_at).toLocaleString("de-DE")} ·{" "}
            {pack.meta.scope_de}
          </p>

          <div>
            <h3 className="text-xs font-semibold text-slate-900">Teil A – Executive Memo</h3>
            <p className="mt-1 text-sm font-medium text-slate-800">{pack.memo.title_de}</p>
            <p className="mt-2 text-[11px] font-medium text-slate-600">Ampel je Säule</p>
            <ul className="mt-1 list-inside list-disc text-xs text-slate-800">
              {pack.memo.pillar_headlines_de.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
            <p className="mt-2 text-[11px] font-medium text-slate-600">Änderungen seit Baseline</p>
            <ul className="mt-1 list-inside list-disc text-xs text-slate-800">
              {pack.memo.changes_since_baseline_de.length ? (
                pack.memo.changes_since_baseline_de.map((l) => <li key={l}>{l}</li>)
              ) : (
                <li>Keine Baseline oder keine erkannten Ampel-Deltas.</li>
              )}
            </ul>
            <p className="mt-2 text-[11px] font-medium text-slate-600">Risiken / Aufmerksamkeit</p>
            <ul className="mt-1 list-inside list-disc text-xs text-slate-800">
              {pack.memo.key_risks_and_concerns_de.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-xs font-semibold text-slate-900">Teil B – Attention Items</h3>
            <div className="mt-2 overflow-x-auto">
              <table className="min-w-full border-collapse text-left text-[11px]">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500">
                    <th className="py-1 pr-2 font-medium">#</th>
                    <th className="py-1 pr-2 font-medium">Regel</th>
                    <th className="py-1 pr-2 font-medium">Ampel</th>
                    <th className="py-1 pr-2 font-medium">Ref</th>
                    <th className="py-1 pr-2 font-medium">Kurztext</th>
                  </tr>
                </thead>
                <tbody>
                  {pack.attention.map((r) => (
                    <tr key={r.reference_id + r.priority_rank} className="border-b border-slate-100 align-top">
                      <td className="py-1 pr-2 font-mono">{r.priority_rank}</td>
                      <td className="py-1 pr-2 text-slate-700">{r.priority_rule_de}</td>
                      <td className="py-1 pr-2 uppercase">{r.severity}</td>
                      <td className="py-1 pr-2 font-mono text-violet-900">{r.reference_id}</td>
                      <td className="py-1 pr-2 text-slate-800">{r.summary_de}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div>
            <h3 className="text-xs font-semibold text-slate-900">Teil C – Aktionsregister</h3>
            <div className="mt-2 overflow-x-auto">
              <table className="min-w-full border-collapse text-left text-[11px]">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500">
                    <th className="py-1 pr-2 font-medium">ID</th>
                    <th className="py-1 pr-2 font-medium">Aktion</th>
                    <th className="py-1 pr-2 font-medium">Säule</th>
                    <th className="py-1 pr-2 font-medium">Owner</th>
                    <th className="py-1 pr-2 font-medium">Horizont</th>
                    <th className="py-1 pr-2 font-medium">Refs</th>
                  </tr>
                </thead>
                <tbody>
                  {pack.actions.map((a) => (
                    <tr key={a.id} className="border-b border-slate-100 align-top">
                      <td className="py-1 pr-2 font-mono">{a.id}</td>
                      <td className="py-1 pr-2 text-slate-800">{a.action_de}</td>
                      <td className="py-1 pr-2">{PILLAR_LABEL[a.pillar] ?? a.pillar}</td>
                      <td className="py-1 pr-2 text-slate-700">{a.owner_de}</td>
                      <td className="py-1 pr-2">{BOARD_PACK_HORIZON_LABEL_DE[a.horizon]}</td>
                      <td className="py-1 pr-2 font-mono text-[10px] text-violet-900">
                        {a.reference_ids.join(", ")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <details className="rounded-lg border border-violet-100 bg-white/70 px-3 py-2 text-xs text-slate-700">
            <summary className="cursor-pointer font-medium text-slate-800">Priorisierungsregeln</summary>
            <ul className="mt-2 list-inside list-disc space-y-1">
              {pack.meta.prioritization_rules_de.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </details>

          <div>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-xs font-semibold text-slate-900">Markdown-Export</h3>
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
              className="mt-2 h-56 w-full resize-y rounded-lg border border-slate-200 bg-slate-50 p-2 font-mono text-[11px] text-slate-800"
              value={pack.markdown_de}
              aria-label="Quarterly Board Pack Markdown"
            />
          </div>

          <p className="text-center text-[10px] text-slate-500">
            Doku:{" "}
            <code className="rounded bg-slate-200/80 px-1">docs/board/wave36-quarterly-board-pack.md</code>
          </p>
        </div>
      ) : null}
    </section>
  );
}
