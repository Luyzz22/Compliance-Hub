import type {
  BoardAttentionItem,
  BoardReadinessPayload,
  BoardReadinessPillarBlock,
  BoardReadinessPillarKey,
  BoardReadinessTraffic,
} from "@/lib/boardReadinessTypes";
import type {
  BoardReadinessBriefingBaselineFile,
  BoardReadinessBriefingPayload,
  BoardReadinessBriefingSection,
  BriefingReference,
} from "@/lib/boardReadinessBriefingTypes";

const PILLAR_TITLES: Record<BoardReadinessPillarKey, string> = {
  eu_ai_act: "EU AI Act",
  iso_42001: "ISO 42001",
  nis2: "NIS2 / KRITIS",
  dsgvo: "DSGVO / Aufzeichnungen",
};

function trafficWort(s: BoardReadinessTraffic): string {
  if (s === "green") return "Grün";
  if (s === "amber") return "Amber";
  return "Rot";
}

/** Referenz-ID für Briefing / Deck (Rückverfolgung im Dashboard). */
export function briefingRefIdForAttentionItem(it: BoardAttentionItem): string {
  if (it.subject_type === "ai_system" && it.subject_id) {
    return `HR-AI-${it.subject_id}`;
  }
  if (it.tenant_id && it.tenant_id !== "_portfolio") {
    return `TENANT-${it.tenant_id}`;
  }
  return `GTM-${it.id.replace(/[^a-zA-Z0-9_-]/g, "_")}`;
}

export function baselineFromPayload(payload: BoardReadinessPayload): BoardReadinessBriefingBaselineFile {
  const pillar_status = {} as Record<BoardReadinessPillarKey, BoardReadinessTraffic>;
  for (const p of payload.pillars) {
    pillar_status[p.pillar] = p.status;
  }
  const red_attention_count = payload.attention_items.filter((a) => a.severity === "red").length;
  const amber_attention_count = payload.attention_items.filter((a) => a.severity === "amber").length;
  return {
    saved_at: new Date().toISOString(),
    source_board_readiness_generated_at: payload.generated_at,
    overall_status: payload.overall.status,
    pillar_status,
    red_attention_count,
    amber_attention_count,
    attention_total: payload.attention_items.length,
  };
}

export function computeDeltaBulletsDe(
  current: BoardReadinessPayload,
  baseline: BoardReadinessBriefingBaselineFile | null,
): string[] {
  if (!baseline) return [];
  const out: string[] = [];

  if (baseline.overall_status !== current.overall.status) {
    out.push(
      `Portfolio-Ampel von „${trafficWort(baseline.overall_status)}“ auf „${trafficWort(current.overall.status)}“ (Baseline: ${new Date(baseline.saved_at).toLocaleDateString("de-DE")}).`,
    );
  }

  for (const p of current.pillars) {
    const prev = baseline.pillar_status[p.pillar];
    if (prev && prev !== p.status) {
      out.push(
        `${PILLAR_TITLES[p.pillar]}: Ampel ${trafficWort(prev)} → ${trafficWort(p.status)}.`,
      );
    }
  }

  const redNow = current.attention_items.filter((a) => a.severity === "red").length;
  if (redNow !== baseline.red_attention_count) {
    out.push(
      `Anzahl roter Attention-Items: ${baseline.red_attention_count} → ${redNow}.`,
    );
  }

  if (out.length === 0) {
    out.push(
      `Keine Änderung der groben Ampeln gegenüber der Baseline vom ${new Date(baseline.saved_at).toLocaleDateString("de-DE")} (Detailkennzahlen können sich dennoch bewegt haben).`,
    );
  }

  return out.slice(0, 5);
}

function sortIndicatorsForBriefing(p: BoardReadinessPillarBlock): BoardReadinessPillarBlock["indicators"] {
  const rank: Record<BoardReadinessTraffic, number> = { red: 0, amber: 1, green: 2 };
  return [...p.indicators].sort((a, b) => rank[a.status] - rank[b.status]);
}

function pillarBullets(p: BoardReadinessPillarBlock): string[] {
  const sorted = sortIndicatorsForBriefing(p);
  const pick = sorted.slice(0, 3);
  return pick.map((ind) => {
    const pct =
      ind.value_percent !== null && ind.value_percent !== undefined
        ? `${Math.round(ind.value_percent * 10) / 10}%`
        : "n. v.";
    return `${ind.label_de}: ${pct}, Ampel ${trafficWort(ind.status)}.`;
  });
}

function attentionBullets(items: BoardAttentionItem[], limit: number): { bullets: string[]; refs: BriefingReference[] } {
  const rank: Record<BoardReadinessTraffic, number> = { red: 0, amber: 1, green: 2 };
  const sorted = [...items].sort((a, b) => rank[a.severity] - rank[b.severity]);
  const slice = sorted.slice(0, limit);
  const refs: BriefingReference[] = [];
  const bullets = slice.map((it) => {
    const rid = briefingRefIdForAttentionItem(it);
    const tenant = it.tenant_label?.trim() || it.tenant_id;
    const seg = it.segment_tag ? ` · Segment ${it.segment_tag}` : "";
    const sys = it.subject_type === "ai_system" && it.subject_name ? ` · „${it.subject_name}“` : "";
    refs.push({
      ref_id: rid,
      context_de: `${it.missing_artefact_de} (${tenant})`,
    });
    return `[${rid}] ${it.missing_artefact_de} · Mandant ${tenant}${sys}${seg} · Ampel ${trafficWort(it.severity)}.`;
  });
  return { bullets, refs };
}

function gtmGovernanceBullets(payload: BoardReadinessPayload): string[] {
  const rows = payload.gtm_demand_strip?.segment_rows ?? [];
  const out: string[] = [];
  for (const r of rows) {
    if (r.qualified_30d >= 3 && r.dominant_readiness === "early_pilot") {
      out.push(
        `${r.label_de}: qualifizierte Nachfrage (${r.qualified_30d} / ${r.inquiries_30d} Anfragen 30d) bei dominanter Readiness „${r.dominant_readiness}“ – Governance nachziehen.`,
      );
    }
    if (r.dominant_readiness === "advanced_governance" && r.qualified_30d <= 1 && r.inquiries_30d >= 4) {
      out.push(
        `${r.label_de}: hohe Eingangslautstärke, wenig Qualifizierung – Pipeline-Thema; Governance-Seite wirkt vorbereitet („${r.dominant_readiness}“).`,
      );
    }
  }
  if (out.length === 0) {
    out.push(
      "Keine automatisch erkannten Extrem-Mismatches im 30-Tage-GTM-Fenster; Details siehe Segment-Tabelle im Dashboard.",
    );
  }
  return out.slice(0, 6);
}

function nextPriorityBullets(payload: BoardReadinessPayload): string[] {
  const rank: Record<BoardReadinessTraffic, number> = { red: 0, amber: 1, green: 2 };
  const sorted = [...payload.attention_items].sort((a, b) => rank[a.severity] - rank[b.severity]);
  const priorities: string[] = [];

  const nextFromItem = (it: BoardAttentionItem): string | null => {
    const rid = briefingRefIdForAttentionItem(it);
    const owner = "Owner: [CCO/CISO – zuweisen]";
    const horizon = "Horizont: bis nächstes Quartals-Update";
    if (it.missing_artefact_de.includes("Board-Report")) {
      return `${owner} · Board-Report aktualisieren (${rid}) · ${horizon}.`;
    }
    if (it.missing_artefact_de.includes("owner_email") || it.missing_artefact_de.includes("Verantwortlicher")) {
      return `${owner} · Verantwortlichen im KI-Register setzen (${rid}) · ${horizon}.`;
    }
    if (it.missing_artefact_de.includes("Art. 9")) {
      return `${owner} · Risikomanagement Art. 9 abschließen (${rid}) · ${horizon}.`;
    }
    if (it.missing_artefact_de.includes("Nachweis") || it.missing_artefact_de.includes("Doku")) {
      return `${owner} · Konformitätsnachweis/Dokumentation schließen (${rid}) · ${horizon}.`;
    }
    if (it.missing_artefact_de.includes("Governance nachziehen")) {
      return `${owner} · Pilot-Mandanten mit Playbook/Setup hochziehen · ${horizon}.`;
    }
    return `${owner} · Lücke schließen: ${it.missing_artefact_de} (${rid}) · ${horizon}.`;
  };

  for (const it of sorted) {
    const line = nextFromItem(it);
    if (line && !priorities.includes(line)) priorities.push(line);
    if (priorities.length >= 3) break;
  }

  if (priorities.length < 3) {
    const redPillars = payload.pillars.filter((p) => p.status === "red").map((p) => PILLAR_TITLES[p.pillar]);
    if (redPillars.length) {
      priorities.push(
        `Owner: [CCO/CISO – zuweisen] · Säulen mit Rot-Ampel gezielt entzerren: ${redPillars.join(", ")} · Horizont: bis nächstes Quartals-Update.`,
      );
    }
  }

  if (priorities.length < 3) {
    priorities.push(
      "Owner: [CCO/CISO – zuweisen] · Kurzes Review der Segment-Rollups im Board-Readiness-Dashboard · Horizont: ad hoc.",
    );
  }

  return priorities.slice(0, 3);
}

export function buildBriefingMarkdownDe(
  title: string,
  generatedAtIso: string,
  sections: BoardReadinessBriefingSection[],
  deltaBullets: string[],
  baselineHint: string | null,
): string {
  const lines: string[] = [`# ${title}`, "", `_Erzeugt: ${generatedAtIso}_`, ""];
  if (baselineHint) {
    lines.push(`> ${baselineHint}`, "");
  }
  if (deltaBullets.length) {
    lines.push("## Delta (gegenüber Baseline)", "");
    for (const d of deltaBullets) lines.push(`- ${d}`);
    lines.push("");
  }
  for (const s of sections) {
    lines.push(`## ${s.heading_de}`, "");
    for (const b of s.bullets) lines.push(`- ${b}`);
    lines.push("");
    if (s.references?.length) {
      lines.push("**Referenzen:**", "");
      for (const r of s.references) lines.push(`- \`${r.ref_id}\`: ${r.context_de}`);
      lines.push("");
    }
  }
  lines.push(
    "---",
    "",
    "_Hinweis: Ausgangspunkt für Redaktion; keine Rechtsberatung. Fachlich und sprachlich vor Board-Einsatz prüfen._",
    "",
  );
  return lines.join("\n");
}

const ATTENTION_LIMIT = 8;

export function generateBoardReadinessBriefing(
  payload: BoardReadinessPayload,
  baseline: BoardReadinessBriefingBaselineFile | null,
): BoardReadinessBriefingPayload {
  const delta_bullets_de = computeDeltaBulletsDe(payload, baseline);

  const execBullets: string[] = [
    `Portfolio: ${trafficWort(payload.overall.status)} – ${payload.overall.label_de}`,
    `Gemappte Mandanten: ${payload.mapped_tenant_count}; Backend-Datenlage: ${payload.backend_reachable ? "überwiegend lesbar" : "teilweise eingeschränkt"}.`,
  ];
  for (const p of payload.pillars) {
    execBullets.push(`${PILLAR_TITLES[p.pillar]}: ${trafficWort(p.status)}.`);
  }
  if (baseline && delta_bullets_de.length) {
    execBullets.push("Änderungen vs. gespeicherter Baseline siehe Abschnitt „Delta“ im Markdown-Export.");
  }

  const pillarBulletLines: string[] = [];
  for (const p of payload.pillars) {
    const label = PILLAR_TITLES[p.pillar];
    const lines = pillarBullets(p);
    if (!lines.length) {
      pillarBulletLines.push(
        `[${label} · ${trafficWort(p.status)}] Keine Indikator-Detailzeilen im aktuellen Schnappschuss.`,
      );
      continue;
    }
    for (const line of lines) {
      pillarBulletLines.push(`[${label} · ${trafficWort(p.status)}] ${line}`);
    }
  }

  const pillarSections: BoardReadinessBriefingSection = {
    id: "pillar_overview",
    heading_de: "2. Säulenüberblick",
    bullets: pillarBulletLines,
  };

  const { bullets: attBullets, refs: attRefs } = attentionBullets(payload.attention_items, ATTENTION_LIMIT);

  const sections: BoardReadinessBriefingSection[] = [
    {
      id: "executive_summary",
      heading_de: "1. Executive Summary",
      bullets: execBullets,
    },
    pillarSections,
    {
      id: "attention_high_risk",
      heading_de: "3. High-Risk / Attention Items (Auswahl)",
      bullets:
        attBullets.length > 0
          ? attBullets
          : ["Keine Attention Items im aktuellen Dashboard-Schnappschuss."],
      references: attRefs.length ? attRefs : undefined,
    },
    {
      id: "gtm_governance",
      heading_de: "4. GTM vs. Governance",
      bullets: gtmGovernanceBullets(payload),
    },
    {
      id: "next_priorities",
      heading_de: "5. Nächste Governance-Prioritäten",
      bullets: nextPriorityBullets(payload),
    },
  ];

  const baselineHint = baseline
    ? `Baseline gespeichert am ${new Date(baseline.saved_at).toLocaleString("de-DE")} (Board-Readiness-Stand ${baseline.source_board_readiness_generated_at}).`
    : null;

  const generated_at = new Date().toISOString();
  const markdown_de = buildBriefingMarkdownDe(
    "Board Readiness Briefing",
    generated_at,
    sections,
    delta_bullets_de,
    baselineHint,
  );

  return {
    generated_at,
    source_board_readiness_generated_at: payload.generated_at,
    outline_version: "wave35-v1",
    sections,
    markdown_de,
    delta_bullets_de,
    baseline_saved_at: baseline?.saved_at ?? null,
    meta_de: {
      mapped_tenant_count: payload.mapped_tenant_count,
      backend_reachable: payload.backend_reachable,
      attention_items_included: Math.min(ATTENTION_LIMIT, payload.attention_items.length),
    },
  };
}
