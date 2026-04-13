"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
  CH_BTN_GHOST,
  CH_CARD,
  CH_SHELL,
  CH_PAGE_TITLE,
  CH_PAGE_SUB,
  CH_SECTION_LABEL,
  CH_BADGE,
} from "@/lib/boardLayout";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface WizardState {
  step: number;
  company: {
    name: string;
    industry: string;
    employeeCount: string;
    complianceAreas: string[];
    handelsregister: string;
    ustIdNr: string;
  };
  frameworks: string[];
  users: { email: string; role: string }[];
  documents: { name: string; sensitivity: string }[];
  completed: boolean;
}

const STORAGE_KEY = "ch_onboarding_wizard";

const INDUSTRIES = [
  { value: "financial_services", label: "Finanzdienstleistung" },
  { value: "healthcare", label: "Gesundheitswesen" },
  { value: "it_tech", label: "IT / Tech" },
  { value: "manufacturing", label: "Produktion" },
  { value: "retail", label: "Handel" },
  { value: "other", label: "Sonstige" },
] as const;

const COMPLIANCE_AREAS = [
  { id: "dsgvo", label: "DSGVO" },
  { id: "nis2", label: "NIS2" },
  { id: "iso27001", label: "ISO 27001" },
  { id: "gobd", label: "GoBD" },
  { id: "eu_ai_act", label: "EU AI Act" },
  { id: "soc2", label: "SOC2" },
] as const;

const FRAMEWORKS = [
  {
    id: "dsgvo",
    name: "DSGVO",
    desc: "Datenschutz-Grundverordnung – Pflicht für alle EU-Unternehmen.",
    effort: "~2–4 Wochen",
  },
  {
    id: "nis2",
    name: "NIS2",
    desc: "Netzwerk- und Informationssicherheit – kritische Infrastrukturen.",
    effort: "~4–8 Wochen",
  },
  {
    id: "iso27001",
    name: "ISO 27001",
    desc: "Informationssicherheits-Managementsystem (ISMS).",
    effort: "~8–16 Wochen",
  },
  {
    id: "gobd",
    name: "GoBD",
    desc: "Grundsätze ordnungsmäßiger Buchführung – steuerliche Pflicht.",
    effort: "~1–2 Wochen",
  },
  {
    id: "eu_ai_act",
    name: "EU AI Act",
    desc: "Regulierung von KI-Systemen nach Risikokategorien.",
    effort: "~3–6 Wochen",
  },
  {
    id: "soc2",
    name: "SOC2",
    desc: "Service Organization Control – für SaaS-/Cloud-Anbieter.",
    effort: "~6–12 Wochen",
  },
] as const;

const ROLES = [
  { value: "admin", label: "Admin" },
  { value: "viewer", label: "Viewer" },
  { value: "auditor", label: "Auditor" },
] as const;

const STEPS = [
  "Unternehmensprofil",
  "Frameworks",
  "Nutzer & Rollen",
  "Trust Center",
  "Zusammenfassung",
] as const;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function defaultState(): WizardState {
  return {
    step: 1,
    company: {
      name: "",
      industry: "",
      employeeCount: "",
      complianceAreas: [],
      handelsregister: "",
      ustIdNr: "",
    },
    frameworks: [],
    users: [{ email: "", role: "admin" }],
    documents: [],
    completed: false,
  };
}

function loadState(): WizardState {
  if (typeof window === "undefined") return defaultState();
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as WizardState) : defaultState();
  } catch {
    return defaultState();
  }
}

function saveState(state: WizardState) {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

// ---------------------------------------------------------------------------
// Stepper
// ---------------------------------------------------------------------------

function Stepper({ current, labels }: { current: number; labels: readonly string[] }) {
  return (
    <nav aria-label="Onboarding-Fortschritt" className="mb-8 flex items-center gap-2">
      {labels.map((label, idx) => {
        const step = idx + 1;
        const isActive = step === current;
        const isDone = step < current;
        return (
          <div key={label} className="flex items-center gap-2">
            <div
              className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold transition ${
                isDone
                  ? "bg-emerald-500 text-white"
                  : isActive
                    ? "bg-cyan-600 text-white"
                    : "bg-slate-200 text-slate-500"
              }`}
            >
              {isDone ? "✓" : step}
            </div>
            <span
              className={`hidden text-xs font-medium sm:inline ${
                isActive ? "text-cyan-700" : "text-slate-500"
              }`}
            >
              {label}
            </span>
            {idx < labels.length - 1 && (
              <div className="mx-1 h-px w-6 bg-slate-300 sm:w-10" />
            )}
          </div>
        );
      })}
    </nav>
  );
}

// ---------------------------------------------------------------------------
// Step Components
// ---------------------------------------------------------------------------

function Step1({
  state,
  onChange,
}: {
  state: WizardState;
  onChange: (s: WizardState) => void;
}) {
  const c = state.company;
  const set = (patch: Partial<typeof c>) =>
    onChange({ ...state, company: { ...c, ...patch } });

  return (
    <section className={CH_CARD}>
      <p className={CH_SECTION_LABEL}>Schritt 1 · Unternehmensprofil</p>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="text-sm font-medium text-slate-700">Firmenname *</span>
          <input
            type="text"
            className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            value={c.name}
            onChange={(e) => set({ name: e.target.value })}
            placeholder="Muster GmbH"
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium text-slate-700">Branche *</span>
          <select
            className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            value={c.industry}
            onChange={(e) => set({ industry: e.target.value })}
          >
            <option value="">Bitte wählen…</option>
            {INDUSTRIES.map((i) => (
              <option key={i.value} value={i.value}>
                {i.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="text-sm font-medium text-slate-700">Mitarbeiteranzahl</span>
          <input
            type="text"
            className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            value={c.employeeCount}
            onChange={(e) => set({ employeeCount: e.target.value })}
            placeholder="z.B. 50–249"
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium text-slate-700">Handelsregisternummer</span>
          <input
            type="text"
            className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            value={c.handelsregister}
            onChange={(e) => set({ handelsregister: e.target.value })}
            placeholder="HRB 12345"
          />
        </label>
        <label className="block sm:col-span-2">
          <span className="text-sm font-medium text-slate-700">USt-IdNr.</span>
          <input
            type="text"
            className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            value={c.ustIdNr}
            onChange={(e) => set({ ustIdNr: e.target.value })}
            placeholder="DE123456789"
          />
        </label>
      </div>
      <fieldset className="mt-4">
        <legend className="text-sm font-medium text-slate-700">
          Haupt-Compliance-Gebiete
        </legend>
        <div className="mt-2 flex flex-wrap gap-3">
          {COMPLIANCE_AREAS.map((area) => {
            const checked = c.complianceAreas.includes(area.id);
            return (
              <label key={area.id} className="flex items-center gap-1.5 text-sm">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => {
                    const next = checked
                      ? c.complianceAreas.filter((a) => a !== area.id)
                      : [...c.complianceAreas, area.id];
                    set({ complianceAreas: next });
                  }}
                />
                {area.label}
              </label>
            );
          })}
        </div>
      </fieldset>
    </section>
  );
}

function Step2({
  state,
  onChange,
}: {
  state: WizardState;
  onChange: (s: WizardState) => void;
}) {
  const toggle = (id: string) => {
    const next = state.frameworks.includes(id)
      ? state.frameworks.filter((f) => f !== id)
      : [...state.frameworks, id];
    onChange({ ...state, frameworks: next });
  };

  return (
    <section className={CH_CARD}>
      <p className={CH_SECTION_LABEL}>Schritt 2 · Compliance-Framework-Auswahl</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {FRAMEWORKS.map((fw) => {
          const selected = state.frameworks.includes(fw.id);
          return (
            <button
              key={fw.id}
              type="button"
              onClick={() => toggle(fw.id)}
              className={`rounded-xl border p-4 text-left transition ${
                selected
                  ? "border-cyan-400 bg-cyan-50 ring-1 ring-cyan-300"
                  : "border-slate-200 bg-white hover:border-slate-300"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-slate-900">{fw.name}</span>
                {selected && (
                  <span className={`${CH_BADGE} bg-cyan-100 text-cyan-700 ring-cyan-200/70`}>
                    ✓ Ausgewählt
                  </span>
                )}
              </div>
              <p className="mt-1 text-xs text-slate-600">{fw.desc}</p>
              <p className="mt-1 text-xs font-medium text-slate-500">
                Geschätzter Aufwand: {fw.effort}
              </p>
            </button>
          );
        })}
      </div>
      {state.frameworks.length > 0 && (
        <div className="mt-4 rounded-lg bg-slate-50 p-3">
          <div className="h-2 overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-full rounded-full bg-cyan-500 transition-all"
              style={{ width: `${(state.frameworks.length / FRAMEWORKS.length) * 100}%` }}
            />
          </div>
          <p className="mt-1 text-xs text-slate-600">
            {state.frameworks.length} von {FRAMEWORKS.length} Frameworks ausgewählt
          </p>
        </div>
      )}
    </section>
  );
}

function Step3({
  state,
  onChange,
}: {
  state: WizardState;
  onChange: (s: WizardState) => void;
}) {
  const users = state.users;
  const setUsers = (next: typeof users) => onChange({ ...state, users: next });

  const addUser = () => {
    if (users.length < 5) {
      setUsers([...users, { email: "", role: "viewer" }]);
    }
  };

  const removeUser = (idx: number) => {
    setUsers(users.filter((_, i) => i !== idx));
  };

  const updateUser = (idx: number, patch: Partial<(typeof users)[0]>) => {
    const next = [...users];
    next[idx] = { ...next[idx], ...patch };
    setUsers(next);
  };

  const adminExists = users.some(
    (u) => u.role === "admin" && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(u.email),
  );

  return (
    <section className={CH_CARD}>
      <p className={CH_SECTION_LABEL}>Schritt 3 · Erstnutzer &amp; Rollenverteilung</p>
      <div className="mt-4 space-y-3">
        {users.map((user, idx) => (
          <div key={idx} className="flex flex-wrap items-end gap-2">
            <label className="flex-1">
              <span className="text-xs font-medium text-slate-600">E-Mail</span>
              <input
                type="email"
                className="mt-0.5 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={user.email}
                onChange={(e) => updateUser(idx, { email: e.target.value })}
                placeholder="max@muster-gmbh.de"
              />
            </label>
            <label className="w-32">
              <span className="text-xs font-medium text-slate-600">Rolle</span>
              <select
                className="mt-0.5 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={user.role}
                onChange={(e) => updateUser(idx, { role: e.target.value })}
              >
                {ROLES.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
            </label>
            {users.length > 1 && (
              <button
                type="button"
                onClick={() => removeUser(idx)}
                className="rounded-lg px-2 py-2 text-sm text-red-500 hover:bg-red-50"
                title="Nutzer entfernen"
              >
                ✕
              </button>
            )}
          </div>
        ))}
      </div>
      {users.length < 5 && (
        <button type="button" onClick={addUser} className={`${CH_BTN_GHOST} mt-3 text-xs`}>
          + Weiteren Nutzer einladen
        </button>
      )}
      {!adminExists && (
        <p className="mt-3 text-xs text-amber-700">
          ⚠️ Mindestens ein Admin mit Firmen-Domain-E-Mail wird benötigt.
        </p>
      )}
    </section>
  );
}

function Step4() {
  return (
    <section className={CH_CARD}>
      <p className={CH_SECTION_LABEL}>Schritt 4 · Trust Center Grundkonfiguration</p>
      <div className="mt-4 space-y-4">
        <div>
          <p className="text-sm font-medium text-slate-700">
            Dokumente hochladen (optional)
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Datenschutzerklärung, ISMS-Policy, Zertifikate – diese können später ergänzt werden.
          </p>
          <div className="mt-2 rounded-xl border-2 border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">
            📄 Drag &amp; Drop oder klicken zum Hochladen
          </div>
        </div>
        <div>
          <p className="text-sm font-medium text-slate-700">
            E-Signing Key Setup
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Für die E-Signatur von Evidence Bundles wird ein ECDSA-P256-Schlüssel benötigt.
            Setzen Sie die Umgebungsvariable <code className="rounded bg-slate-100 px-1 py-0.5 text-xs font-mono">TRUST_CENTER_SIGNING_KEYS</code>.
          </p>
          <div className="mt-2 rounded-lg bg-slate-900 p-3">
            <code className="block text-xs text-emerald-400">
              openssl ecparam -genkey -name prime256v1 | openssl pkcs8 -topk8 -nocrypt
            </code>
          </div>
          <button
            type="button"
            className={`${CH_BTN_GHOST} mt-2 text-xs`}
            onClick={() => {
              navigator.clipboard?.writeText(
                "openssl ecparam -genkey -name prime256v1 | openssl pkcs8 -topk8 -nocrypt"
              );
            }}
          >
            📋 Befehl kopieren
          </button>
        </div>
      </div>
    </section>
  );
}

function Step5({ state }: { state: WizardState }) {
  return (
    <section className={CH_CARD}>
      <p className={CH_SECTION_LABEL}>Schritt 5 · Zusammenfassung &amp; Launch</p>
      <div className="mt-4 space-y-3 text-sm text-slate-700">
        <div>
          <span className="font-semibold">Unternehmen:</span>{" "}
          {state.company.name || "–"}
          {state.company.industry &&
            ` (${INDUSTRIES.find((i) => i.value === state.company.industry)?.label ?? state.company.industry})`}
        </div>
        <div>
          <span className="font-semibold">Frameworks:</span>{" "}
          {state.frameworks.length > 0
            ? state.frameworks
                .map((f) => FRAMEWORKS.find((fw) => fw.id === f)?.name ?? f)
                .join(", ")
            : "–"}
        </div>
        <div>
          <span className="font-semibold">Eingeladene Nutzer:</span>{" "}
          {state.users.filter((u) => u.email).length > 0
            ? state.users
                .filter((u) => u.email)
                .map((u) => `${u.email} (${u.role})`)
                .join(", ")
            : "–"}
        </div>
        {state.company.handelsregister && (
          <div>
            <span className="font-semibold">Handelsregister:</span>{" "}
            {state.company.handelsregister}
          </div>
        )}
        {state.company.ustIdNr && (
          <div>
            <span className="font-semibold">USt-IdNr.:</span> {state.company.ustIdNr}
          </div>
        )}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function OnboardingWizardPage() {
  const router = useRouter();
  const [state, setState] = useState<WizardState>(loadState);

  // Persist on every change — skip when completed to avoid race condition
  useEffect(() => {
    if (state.completed) return;
    saveState(state);
  }, [state]);

  const canNext = useMemo(() => {
    if (state.step === 1) return state.company.name.trim().length > 0;
    return true;
  }, [state]);

  const next = useCallback(() => {
    if (state.step < STEPS.length) {
      setState((s) => ({ ...s, step: s.step + 1 }));
    }
  }, [state.step]);

  const prev = useCallback(() => {
    if (state.step > 1) {
      setState((s) => ({ ...s, step: s.step - 1 }));
    }
  }, [state.step]);

  const finish = useCallback(() => {
    sessionStorage.removeItem(STORAGE_KEY);
    router.push("/tenant/compliance-overview");
  }, [router]);

  return (
    <div className={CH_SHELL}>
      <div>
        <p className={CH_PAGE_TITLE}>Willkommen bei Compliance Hub 🚀</p>
        <p className={CH_PAGE_SUB}>
          Richten Sie Ihre Compliance-Umgebung in wenigen Schritten ein. Jeder Schritt kann
          übersprungen und später nachgeholt werden.
        </p>
      </div>

      <Stepper current={state.step} labels={STEPS} />

      {state.step === 1 && <Step1 state={state} onChange={setState} />}
      {state.step === 2 && <Step2 state={state} onChange={setState} />}
      {state.step === 3 && <Step3 state={state} onChange={setState} />}
      {state.step === 4 && <Step4 />}
      {state.step === 5 && <Step5 state={state} />}

      <div className="flex flex-wrap items-center gap-3">
        {state.step > 1 && (
          <button type="button" onClick={prev} className={CH_BTN_SECONDARY}>
            ← Zurück
          </button>
        )}
        {state.step < STEPS.length && (
          <button
            type="button"
            onClick={next}
            disabled={!canNext}
            className={`${CH_BTN_PRIMARY} ${!canNext ? "opacity-50" : ""}`}
          >
            Weiter →
          </button>
        )}
        {state.step === STEPS.length && (
          <button type="button" onClick={finish} className={CH_BTN_PRIMARY}>
            🎉 Compliance Hub starten
          </button>
        )}
        <button
          type="button"
          onClick={() => router.push("/tenant/compliance-overview")}
          className={`${CH_BTN_GHOST} ml-auto text-xs text-slate-500`}
        >
          Später einrichten →
        </button>
      </div>
    </div>
  );
}
