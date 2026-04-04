import type { TenantBoardReadinessRaw } from "@/lib/tenantBoardReadinessRawTypes";
import {
  classifyMappedTenantReadiness,
  GTM_READINESS_LABELS_DE,
  type GtmGovernanceSignalsInput,
} from "@/lib/gtmAccountReadiness";
import type {
  MandantReadinessAdvisorMeta,
  MandantReadinessAdvisorPayload,
  MandantReadinessKompakt,
  MandantReadinessNaechsterSchritt,
  MandantReadinessNachweisHinweis,
  MandantReadinessOffenerPunktExport,
} from "@/lib/mandantReadinessAdvisorTypes";
import { MANDANT_READINESS_EXPORT_VERSION } from "@/lib/mandantReadinessAdvisorTypes";
import {
  computeMandantOffenePunkte,
  type MandantOffenerPunkt,
} from "@/lib/tenantBoardReadinessGaps";

function govInputFromSnapshots(
  aiCount: number,
  progress: number[],
  frameworks: string[],
  fetchOk: boolean,
  pilot: boolean,
): GtmGovernanceSignalsInput {
  return {
    ai_systems_count: aiCount,
    progress_steps: progress,
    active_frameworks: frameworks,
    fetch_ok: fetchOk,
    pilot_flag: pilot,
  };
}

function ansprechpartnerAusSetup(raw: TenantBoardReadinessRaw): string {
  const roles = raw.ai_governance_setup?.governance_roles ?? {};
  const entries = Object.entries(roles).filter(([, v]) => String(v || "").trim());
  if (!entries.length) {
    return "Ansprechpartner / Verantwortliche im Mandanten-Setup (AI-Governance) ergänzen.";
  }
  return entries
    .slice(0, 4)
    .map(([k, v]) => `${k}: ${v}`)
    .join(" · ");
}

function hauptbedenken(
  punkte: MandantOffenerPunkt[],
  euIncomplete: number | undefined,
): string[] {
  const out: string[] = [];
  const hoch = punkte.filter((p) => p.dringlichkeit === "hoch");
  for (const p of hoch.slice(0, 3)) {
    out.push(p.pruefpunkt_de);
  }
  if (euIncomplete && euIncomplete > 0) {
    out.push(
      `${euIncomplete} Hochrisiko-KI-System(e) mit unvollständigen Pflichtnachweisen (EU AI Act, laut Systemübersicht).`,
    );
  }
  if (!out.length) {
    out.push("Keine automatisch als „hoch“ priorisierten Prüfpunkte; stichprobenartige Prüfung dennoch empfohlen.");
  }
  return out.slice(0, 5);
}

function schritteAusPunkten(punkte: MandantOffenerPunkt[]): MandantReadinessNaechsterSchritt[] {
  const out: MandantReadinessNaechsterSchritt[] = [];
  for (const p of punkte.slice(0, 5)) {
    if (p.dringlichkeit === "hoch" && p.ki_system_id) {
      out.push({
        schritt_de: `Mit Mandant klären: Verantwortung und Frist für „${p.ki_system_name ?? p.ki_system_id}“ (${p.referenz_id}).`,
        fuer: "gemeinsam",
      });
    }
    if (p.id.startsWith("board:")) {
      out.push({
        schritt_de: `Aktuellen Mandanten-/Board-Report erzeugen oder aktualisieren (${p.referenz_id}).`,
        fuer: "mandant",
      });
    }
  }
  out.push({
    schritt_de: "Kanzlei: Prüfpunkte mit Jahresabschluss-/Beratungsgespräch abstimmen und dokumentieren.",
    fuer: "kanzlei",
  });
  out.push({
    schritt_de: "Mandant: offene technische Nachweise in ComplianceHub schließen (siehe Referenzen).",
    fuer: "mandant",
  });
  const seen = new Set<string>();
  return out.filter((s) => (seen.has(s.schritt_de) ? false : (seen.add(s.schritt_de), true))).slice(0, 6);
}

function nachweiseBlock(
  tenantId: string,
  raw: TenantBoardReadinessRaw,
  punkte: MandantOffenerPunkt[],
): MandantReadinessNachweisHinweis[] {
  const br = raw.board_reports[0];
  const refs = [...new Set(punkte.map((p) => p.referenz_id))];
  return [
    {
      label_de: "Mandanten-ID (System)",
      wert_de: tenantId,
    },
    {
      label_de: "Letzter gespeicherter Board-/Compliance-Report (falls vorhanden)",
      wert_de: br
        ? `${br.title} · ${br.created_at} · ID ${br.id}`
        : "Kein Eintrag in der Report-Liste.",
    },
    {
      label_de: "Referenz-IDs (Prüfpunkte)",
      wert_de: refs.length ? refs.join(", ") : "—",
    },
    {
      label_de: "DATEV / Kanzlei-Workflow",
      wert_de:
        "Dieses Dokument ist ein Arbeitspapier-Export aus ComplianceHub. Anlage in der Kanzlei-DMS oder Übergabe an DATEV erfolgt manuell; strukturierte Rohdaten ggf. über Mandanten-API.",
    },
  ];
}

export function buildMandantReadinessMarkdownDe(payload: MandantReadinessAdvisorPayload): string {
  const k = payload.kompakt;
  const lines: string[] = [
    `# Mandantenstatus – Readiness (Kanzlei / Berater)`,
    "",
    `_Erzeugt: ${payload.meta.generated_at} · Mandant: ${k.mandant_id}_`,
    "",
    "## 1. Mandantenstatus kompakt",
    "",
    `- **Bezeichnung:** ${k.mandanten_bezeichnung}`,
    `- **Readiness (Kurz):** ${k.readiness_kurzfassung_de}`,
    `- **KI-Anwendungen gesamt:** ${k.ki_systeme_gesamt} · **Hochrisiko (klassifiziert):** ${k.ki_hochrisiko_anzahl}`,
    `- **Governance-Reife (Orientierung):** ${k.governance_reifeklasse_de}`,
    `- **Ansprechpartner / Rollen:** ${k.ansprechpartner_hinweis_de}`,
    "",
    "**Aktuelle Schwerpunkte / Risiken:**",
    ...k.hauptbedenken_de.map((x) => `- ${x}`),
    "",
    "## 2. Offene Punkte (Prüfpunkte)",
    "",
    "| Priorität | Prüfpunkt | Referenz | KI-System | Stand (letzte Änderung) |",
    "| --- | --- | --- | --- | --- |",
    ...payload.offene_punkte.map(
      (o) =>
        `| ${o.prioritaet} | ${o.pruefpunkt_de.replace(/\|/g, "/")} | \`${o.referenz_id}\` | ${(o.ki_system ?? "—").replace(/\|/g, "/")} | ${o.letzte_aenderung_iso ?? "—"} |`,
    ),
    "",
    "## 3. Nächste Schritte (Mandant & Kanzlei)",
    "",
    ...payload.naechste_schritte.map((s) => `- **${s.fuer}:** ${s.schritt_de}`),
    "",
    "## 4. Nachweise & Exporthinweise",
    "",
    ...payload.nachweise.map((n) => `- **${n.label_de}:** ${n.wert_de}`),
    "",
    "---",
    "",
    payload.meta.hinweis_de,
    "",
  ];
  return lines.join("\n");
}

export function generateMandantReadinessAdvisorExport(input: {
  mandantId: string;
  mandantenBezeichnung: string;
  raw: TenantBoardReadinessRaw;
  pilotFlag: boolean;
  nowMs: number;
}): MandantReadinessAdvisorPayload {
  const { mandantId, mandantenBezeichnung, raw, pilotFlag, nowMs } = input;

  const aiCount = raw.ai_systems.length;
  const progress = raw.ai_governance_setup?.progress_steps ?? [];
  const fw = raw.ai_governance_setup?.active_frameworks ?? [];
  const fetchOk = raw.fetch_ok;
  const reife = classifyMappedTenantReadiness(
    govInputFromSnapshots(aiCount, progress, fw, fetchOk, pilotFlag),
  );
  const reifeLabel = GTM_READINESS_LABELS_DE[reife];

  const hrCount =
    raw.compliance_dashboard?.systems.filter((s) => s.risk_level === "high_risk").length ?? 0;

  const eu = raw.eu_ai_act_readiness;
  const euPct =
    eu?.overall_readiness !== undefined ? Math.round((eu.overall_readiness as number) * 1000) / 10 : null;
  const euIncomplete = eu?.high_risk_systems_essential_incomplete;

  const punkte = computeMandantOffenePunkte(mandantId, raw, nowMs);

  const readinessKurz =
    euPct !== null
      ? `EU-AI-Act-Readiness ca. ${euPct} % (rechnerisch aus Pflichtnachweisen; keine Rechtsbewertung). ${hrCount} Hochrisiko-Systeme im Überblick.`
      : `Datenlage eingeschränkt oder Readiness nicht berechenbar. ${hrCount} Hochrisiko-Systeme laut Klassifikationsübersicht (falls vorhanden).`;

  const kompakt: MandantReadinessKompakt = {
    mandant_id: mandantId,
    mandanten_bezeichnung: mandantenBezeichnung,
    readiness_kurzfassung_de: readinessKurz,
    ki_systeme_gesamt: aiCount,
    ki_hochrisiko_anzahl: hrCount,
    governance_reifeklasse_de: reifeLabel,
    ansprechpartner_hinweis_de: ansprechpartnerAusSetup(raw),
    hauptbedenken_de: hauptbedenken(punkte, euIncomplete),
  };

  const offene_punkte: MandantReadinessOffenerPunktExport[] = punkte.map((p) => ({
    prioritaet: p.dringlichkeit,
    pruefpunkt_de: p.pruefpunkt_de,
    referenz_id: p.referenz_id,
    ki_system: p.ki_system_name ?? p.ki_system_id,
    letzte_aenderung_iso: p.letzte_aenderung_iso ?? null,
  }));

  const naechste_schritte = schritteAusPunkten(punkte);
  const nachweise = nachweiseBlock(mandantId, raw, punkte);

  const meta: MandantReadinessAdvisorMeta = {
    generated_at: new Date(nowMs).toISOString(),
    quelle_dashboard_stand: raw.fetch_ok ? "API-Antworten zum Erstellungszeitpunkt" : "teilweise nicht lesbar",
    api_erreichbar: raw.fetch_ok,
    hinweis_de:
      "Internes Arbeitspapier für Steuerberater, Wirtschaftsprüfer und GRC-/ISMS-Berater. Keine Rechtsberatung; vor Weitergabe an Dritte redaktionell prüfen.",
  };

  const payload: MandantReadinessAdvisorPayload = {
    version: MANDANT_READINESS_EXPORT_VERSION,
    kompakt,
    offene_punkte,
    naechste_schritte,
    nachweise,
    markdown_de: "",
    meta,
  };
  payload.markdown_de = buildMandantReadinessMarkdownDe(payload);
  return payload;
}
