"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  deleteEvidenceFile,
  downloadEvidenceBlob,
  fetchEvidenceList,
  uploadEvidenceFile,
  type EvidenceFile,
  type EvidenceListFilter,
} from "@/lib/api";
import { CH_BTN_PRIMARY, CH_BTN_SECONDARY } from "@/lib/boardLayout";

function formatBytes(n: number): string {
  if (n < 1024) {
    return `${n} B`;
  }
  if (n < 1024 * 1024) {
    return `${(n / 1024).toFixed(1)} KB`;
  }
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function docIcon(ct: string, filename: string): string {
  const f = filename.toLowerCase();
  if (ct.includes("pdf") || f.endsWith(".pdf")) {
    return "PDF";
  }
  if (ct.includes("spreadsheet") || f.endsWith(".xlsx")) {
    return "XLS";
  }
  if (ct.includes("word") || f.endsWith(".docx")) {
    return "DOC";
  }
  if (ct.includes("png") || f.endsWith(".png")) {
    return "PNG";
  }
  if (ct.includes("jpeg") || f.endsWith(".jpg") || f.endsWith(".jpeg")) {
    return "JPG";
  }
  return "FILE";
}

export function EvidenceAttachmentsSection(props: {
  title?: string;
  description: string;
  aiSystemId?: string;
  auditRecordId?: string;
  actionId?: string;
  compact?: boolean;
}) {
  const {
    title = "Evidenz & Belege",
    description,
    aiSystemId,
    auditRecordId,
    actionId,
    compact,
  } = props;

  const filter: EvidenceListFilter | null = useMemo(() => {
    const n = [aiSystemId, auditRecordId, actionId].filter(Boolean).length;
    if (n !== 1) {
      return null;
    }
    if (aiSystemId) {
      return { ai_system_id: aiSystemId };
    }
    if (auditRecordId) {
      return { audit_record_id: auditRecordId };
    }
    if (actionId) {
      return { action_id: actionId };
    }
    return null;
  }, [aiSystemId, auditRecordId, actionId]);

  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [items, setItems] = useState<EvidenceFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [normFw, setNormFw] = useState("");
  const [normRef, setNormRef] = useState("");

  const load = useCallback(async () => {
    if (!filter) {
      setItems([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setMessage(null);
    try {
      const list = await fetchEvidenceList(filter);
      setItems(list);
    } catch (e) {
      setMessage(
        e instanceof Error ? e.message : "Evidenzliste konnte nicht geladen werden."
      );
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    void load();
  }, [load]);

  async function onUpload() {
    if (!filter) {
      return;
    }
    const file = inputRef.current?.files?.[0];
    if (!file) {
      setMessage("Bitte eine Datei wählen (PDF, DOCX, XLSX, PNG, JPEG).");
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      await uploadEvidenceFile(file, {
        ...("ai_system_id" in filter ? { ai_system_id: filter.ai_system_id } : {}),
        ...("audit_record_id" in filter
          ? { audit_record_id: filter.audit_record_id }
          : {}),
        ...("action_id" in filter ? { action_id: filter.action_id } : {}),
        norm_framework: normFw.trim() || undefined,
        norm_reference: normRef.trim() || undefined,
      });
      if (inputRef.current) {
        inputRef.current.value = "";
      }
      await load();
      router.refresh();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Upload fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  }

  async function onDownload(ev: EvidenceFile) {
    setMessage(null);
    try {
      const blob = await downloadEvidenceBlob(ev.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = ev.filename_original;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Download fehlgeschlagen.");
    }
  }

  async function onDelete(id: string) {
    if (!globalThis.confirm("Diese Evidenz wirklich löschen?")) {
      return;
    }
    setMessage(null);
    try {
      await deleteEvidenceFile(id);
      await load();
      router.refresh();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Löschen fehlgeschlagen.");
    }
  }

  if (!filter) {
    return (
      <p className="text-xs text-rose-700">
        Interne Konfiguration: genau ein Kontext (System, Audit-Record oder Maßnahme)
        erforderlich.
      </p>
    );
  }

  const shell = compact
    ? "rounded-xl border border-slate-200/80 bg-white/90 p-3"
    : "rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm";

  return (
    <div className={shell}>
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      <p className="mt-1 text-xs leading-relaxed text-slate-600">{description}</p>

      <div className="mt-3 flex flex-wrap items-end gap-2">
        <div className="min-w-[10rem] flex-1">
          <label className="text-[10px] font-medium uppercase tracking-wide text-slate-500">
            Datei
          </label>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.docx,.xlsx,.png,.jpg,.jpeg,application/pdf,image/*"
            className="mt-0.5 block w-full text-xs text-slate-700 file:mr-2 file:rounded-lg file:border-0 file:bg-cyan-50 file:px-2 file:py-1.5 file:text-xs file:font-semibold file:text-cyan-900"
          />
        </div>
        <input
          type="text"
          placeholder="Norm (z. B. EUAIACT)"
          value={normFw}
          onChange={(e) => setNormFw(e.target.value)}
          className="w-28 rounded-lg border border-slate-200 px-2 py-1.5 text-xs"
        />
        <input
          type="text"
          placeholder="Ref. (z. B. Art. 9)"
          value={normRef}
          onChange={(e) => setNormRef(e.target.value)}
          className="w-32 rounded-lg border border-slate-200 px-2 py-1.5 text-xs"
        />
        <button
          type="button"
          disabled={busy}
          className={`${CH_BTN_PRIMARY} px-3 py-2 text-xs`}
          onClick={() => void onUpload()}
        >
          {busy ? "…" : "Hochladen"}
        </button>
      </div>

      {message ? (
        <p
          className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-2 py-1.5 text-xs text-amber-950"
          role="status"
        >
          {message}
        </p>
      ) : null}

      <div className="mt-3 overflow-x-auto">
        {loading ? (
          <p className="text-xs text-slate-500">Lade Evidenzen…</p>
        ) : items.length === 0 ? (
          <p className="text-xs text-slate-500">Noch keine Dateien hinterlegt.</p>
        ) : (
          <table className="w-full min-w-[280px] text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-2">Typ</th>
                <th className="py-2 pr-2">Name</th>
                <th className="py-2 pr-2">Größe</th>
                <th className="py-2 pr-2">Datum</th>
                <th className="py-2 pr-2">Norm</th>
                <th className="py-2 text-right">Aktion</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((ev) => (
                <tr key={ev.id} className="text-slate-800">
                  <td className="py-2 pr-2">
                    <span className="inline-flex rounded-md bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-slate-700">
                      {docIcon(ev.content_type, ev.filename_original)}
                    </span>
                  </td>
                  <td className="max-w-[140px] truncate py-2 pr-2 font-medium">
                    {ev.filename_original}
                  </td>
                  <td className="py-2 pr-2 tabular-nums text-slate-600">
                    {formatBytes(ev.size_bytes)}
                  </td>
                  <td className="py-2 pr-2 text-slate-600">
                    {new Date(ev.created_at).toLocaleString("de-DE", {
                      dateStyle: "short",
                      timeStyle: "short",
                    })}
                  </td>
                  <td className="max-w-[100px] truncate py-2 pr-2 text-slate-600">
                    {ev.norm_framework || ev.norm_reference
                      ? [ev.norm_framework, ev.norm_reference].filter(Boolean).join(" · ")
                      : "–"}
                  </td>
                  <td className="py-2 text-right">
                    <div className="flex flex-wrap justify-end gap-1">
                      <button
                        type="button"
                        className={`${CH_BTN_SECONDARY} px-2 py-1 text-[10px]`}
                        onClick={() => void onDownload(ev)}
                      >
                        Download
                      </button>
                      <button
                        type="button"
                        className="rounded-lg border border-rose-200 bg-rose-50 px-2 py-1 text-[10px] font-semibold text-rose-900 hover:bg-rose-100"
                        onClick={() => void onDelete(ev.id)}
                      >
                        Löschen
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
