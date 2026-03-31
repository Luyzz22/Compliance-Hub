"use client";

import React, { useState } from "react";

import {
  createAIGovernanceAction,
  postAiGovernanceActionDrafts,
  type AIGovernanceActionDraft,
  type ReadinessRequirementTraffic,
} from "@/lib/api";
import { CH_BTN_PRIMARY, CH_BTN_SECONDARY } from "@/lib/boardLayout";
import { featureLlmActionDrafts, featureLlmEnabled } from "@/lib/config";

type Props = {
  code: string;
  name: string;
  traffic: ReadinessRequirementTraffic;
  requirementId?: string | null;
  relatedAiSystemId?: string | null;
};

function gapText(traffic: ReadinessRequirementTraffic): string {
  switch (traffic) {
    case "red":
      return "Wesentliche Lücken / roter Ampelstatus in der Readiness-Heuristik.";
    case "amber":
      return "Teilweise Umsetzung; gelber Ampelstatus.";
    default:
      return "Grüner Ampelstatus; dennoch fortlaufende Pflege empfohlen.";
  }
}

export function ReadinessActionDraftButton({
  code,
  name,
  traffic,
  requirementId,
  relatedAiSystemId,
}: Props) {
  const enabled = featureLlmEnabled() && featureLlmActionDrafts();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<AIGovernanceActionDraft[] | null>(null);
  const [adopting, setAdopting] = useState<string | null>(null);

  if (!enabled) return null;

  const loadDrafts = async () => {
    setLoading(true);
    setErr(null);
    try {
      const res = await postAiGovernanceActionDrafts({
        ai_system_id: relatedAiSystemId ?? null,
        requirements: [
          {
            framework: "EU_AI_ACT",
            reference: requirementId ?? `${code}: ${name}`,
            gap_description: `${gapText(traffic)} Anforderung ${code} – ${name}.`,
          },
        ],
      });
      setDrafts(res.drafts);
      setOpen(true);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Anfrage fehlgeschlagen");
    } finally {
      setLoading(false);
    }
  };

  const adopt = async (d: AIGovernanceActionDraft) => {
    const key = d.title;
    setAdopting(key);
    try {
      await createAIGovernanceAction({
        related_ai_system_id: relatedAiSystemId ?? null,
        related_requirement: `${d.framework} ${d.reference}`.trim(),
        title: d.title,
        owner: d.suggested_role,
        status: "open",
      });
      setOpen(false);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Speichern fehlgeschlagen");
    } finally {
      setAdopting(null);
    }
  };

  return (
    <div className="mt-2">
      <button
        type="button"
        className={`${CH_BTN_SECONDARY} px-3 py-1.5 text-xs`}
        disabled={loading}
        onClick={() => void loadDrafts()}
      >
        {loading ? "Laden…" : "Maßnahmen vorschlagen lassen"}
      </button>
      {err ? <p className="mt-1 text-xs text-red-600">{err}</p> : null}
      {open && drafts ? (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/40 p-4 sm:items-center"
          role="dialog"
          aria-modal="true"
          aria-label="Action-Entwürfe"
        >
          <div className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-5 shadow-xl">
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-base font-semibold text-slate-900">
                KI-Entwürfe (nicht persistiert)
              </h3>
              <button
                type="button"
                className="rounded-lg px-2 py-1 text-sm text-slate-500 hover:bg-slate-100"
                onClick={() => setOpen(false)}
              >
                Schließen
              </button>
            </div>
            <p className="mt-2 text-xs text-amber-900">
              AI-Vorschlag – fachliche Freigabe erforderlich vor Umsetzung.
            </p>
            <ul className="mt-4 space-y-3 text-sm">
              {drafts.map((d) => (
                <li
                  key={`${d.title}-${d.reference}`}
                  className="rounded-xl border border-slate-200 bg-slate-50/80 p-3"
                >
                  <p className="font-semibold text-slate-900">{d.title}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {d.framework} · {d.reference} · Prio {d.priority} · Rolle:{" "}
                    {d.suggested_role}
                  </p>
                  <p className="mt-2 text-slate-700">{d.description}</p>
                  <button
                    type="button"
                    className={`${CH_BTN_PRIMARY} mt-2 text-xs`}
                    disabled={adopting === d.title}
                    onClick={() => void adopt(d)}
                  >
                    {adopting === d.title ? "Anlegen…" : "Als Action übernehmen"}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      ) : null}
    </div>
  );
}
