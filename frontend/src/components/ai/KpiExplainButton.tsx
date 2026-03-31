"use client";

import React, { useCallback, useState } from "react";

import {
  postAiGovernanceExplain,
  type ExplainRequestInput,
  type ExplainResponsePayload,
} from "@/lib/api";
import { CH_BTN_SECONDARY } from "@/lib/boardLayout";
import { featureLlmEnabled, featureLlmExplain } from "@/lib/config";

type Props = {
  label?: string;
  request: ExplainRequestInput;
  className?: string;
};

export function KpiExplainButton({
  label = "Was bedeutet das?",
  request,
  className,
}: Props) {
  const enabled = featureLlmEnabled() && featureLlmExplain();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [data, setData] = useState<ExplainResponsePayload | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const res = await postAiGovernanceExplain(request);
      setData(res);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Anfrage fehlgeschlagen");
    } finally {
      setLoading(false);
    }
  }, [request]);

  if (!enabled) return null;

  return (
    <>
      <button
        type="button"
        className={className ?? `${CH_BTN_SECONDARY} px-2 py-1 text-xs`}
        onClick={() => {
          setOpen(true);
          void load();
        }}
      >
        {label}
      </button>
      {open ? (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/40 p-4 sm:items-center"
          role="dialog"
          aria-modal="true"
          aria-label="KPI-Erklärung"
        >
          <div className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-5 shadow-xl">
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-base font-semibold text-slate-900">
                {data?.title ?? "Erklärung"}
              </h3>
              <button
                type="button"
                className="rounded-lg px-2 py-1 text-sm text-slate-500 hover:bg-slate-100"
                onClick={() => setOpen(false)}
              >
                Schließen
              </button>
            </div>
            <p className="mt-2 text-xs text-amber-800">
              KI-generierte Erklärung – vor Umsetzung mit internen Richtlinien abgleichen.
            </p>
            {loading ? (
              <p className="mt-4 text-sm text-slate-600">Laden…</p>
            ) : err ? (
              <p className="mt-4 text-sm text-red-700">{err}</p>
            ) : data ? (
              <div className="mt-4 space-y-4 text-sm text-slate-700">
                <p className="leading-relaxed">{data.summary}</p>
                {data.why_it_matters.length > 0 ? (
                  <div>
                    <p className="font-semibold text-slate-900">Warum wichtig</p>
                    <ul className="mt-2 list-disc space-y-1 pl-5">
                      {data.why_it_matters.map((x) => (
                        <li key={x}>{x}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {data.suggested_actions.length > 0 ? (
                  <div>
                    <p className="font-semibold text-slate-900">Typische nächste Schritte</p>
                    <ul className="mt-2 list-disc space-y-1 pl-5">
                      {data.suggested_actions.map((x) => (
                        <li key={x}>{x}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </>
  );
}
