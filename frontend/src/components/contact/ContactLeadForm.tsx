"use client";

import { useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

import { CH_BTN_PRIMARY, CH_BTN_SECONDARY } from "@/lib/boardLayout";
import { LEAD_SEGMENTS } from "@/lib/leadCapture";
import { sendMarketingEvent } from "@/lib/marketingTelemetryClient";
import { PUBLIC_CONTACT_EMAIL, PUBLIC_CONTACT_MAILTO } from "@/lib/publicContact";

type Status = "idle" | "submitting" | "success" | "error";

export function ContactLeadForm() {
  const sp = useSearchParams();
  const quelleRaw = sp.get("quelle");
  const quelle =
    quelleRaw && quelleRaw.trim() ? quelleRaw.trim().slice(0, 120) : "kontakt-direct";

  const startedRef = useRef(false);
  const [status, setStatus] = useState<Status>("idle");
  const [errorDetail, setErrorDetail] = useState<string | null>(null);

  const markStarted = () => {
    if (startedRef.current) return;
    startedRef.current = true;
    sendMarketingEvent({
      event: "lead_form_started",
      quelle,
    });
  };

  const clearError = () => {
    if (status === "error") {
      setStatus("idle");
      setErrorDetail(null);
    }
  };

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setErrorDetail(null);
    sendMarketingEvent({ event: "lead_form_submit_attempt", quelle });
    setStatus("submitting");

    const fd = new FormData(e.currentTarget);
    const company_website = (fd.get("company_website") as string) || "";
    const payload = {
      name: (fd.get("name") as string) || "",
      work_email: (fd.get("work_email") as string) || "",
      company: (fd.get("company") as string) || "",
      segment: (fd.get("segment") as string) || "",
      message: (fd.get("message") as string) || "",
      source_page: quelle,
      company_website,
    };

    try {
      const res = await fetch("/api/lead-inquiry", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        setStatus("error");
        setErrorDetail("validation");
        sendMarketingEvent({ event: "lead_form_submit_error", quelle });
        return;
      }
      setStatus("success");
      sendMarketingEvent({ event: "lead_form_submitted", quelle });
      e.currentTarget.reset();
    } catch {
      setStatus("error");
      setErrorDetail("network");
      sendMarketingEvent({ event: "lead_form_submit_error", quelle });
    }
  }

  if (status === "success") {
    return (
      <div
        className="rounded-2xl border border-emerald-200/90 bg-emerald-50/50 p-6 shadow-sm"
        role="status"
        aria-live="polite"
      >
        <p className="text-sm font-semibold text-emerald-900">Vielen Dank für Ihre Anfrage.</p>
        <p className="mt-2 text-sm leading-relaxed text-emerald-900/90">
          Wir prüfen Ihre Angaben und melden uns in der Regel innerhalb weniger Werktage bei Ihnen.
          Die Anfrage ist unverbindlich und begründet keine rechtsverbindliche Zusage.
        </p>
        <p className="mt-3 text-xs text-emerald-900/80">
          Hinweis: Erstkontakt ersetzt keine Rechts- oder Steuerberatung.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-200/90 bg-white p-6 shadow-md shadow-slate-200/40 sm:p-8">
      <p className="text-sm leading-relaxed text-slate-600">
        Füllen Sie die Pflichtfelder aus. Wir nutzen Ihre geschäftliche E-Mail ausschließlich zur
        Bearbeitung dieser Anfrage. Die Anfrage ist <strong>unverbindlich</strong>. Es entstehen
        keine automatischen Verträge. Erstkontakt ersetzt <strong>keine Rechtsberatung</strong>.
      </p>

      <form className="relative mt-6 space-y-4" onSubmit={onSubmit} noValidate>
        {/* Honeypot */}
        <div className="absolute -left-[9999px] h-0 w-0 overflow-hidden" aria-hidden="true">
          <label htmlFor="company_website">Website</label>
          <input
            type="text"
            id="company_website"
            name="company_website"
            tabIndex={-1}
            autoComplete="off"
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="lead-name" className="block text-xs font-semibold text-slate-700">
              Name <span className="text-red-600">*</span>
            </label>
            <input
              id="lead-name"
              name="name"
              type="text"
              required
              autoComplete="name"
              maxLength={120}
              onFocus={markStarted}
              onChange={clearError}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
            />
          </div>
          <div>
            <label htmlFor="lead-email" className="block text-xs font-semibold text-slate-700">
              Geschäftliche E-Mail <span className="text-red-600">*</span>
            </label>
            <input
              id="lead-email"
              name="work_email"
              type="email"
              required
              autoComplete="email"
              maxLength={254}
              onFocus={markStarted}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
            />
          </div>
        </div>

        <div>
          <label htmlFor="lead-company" className="block text-xs font-semibold text-slate-700">
            Unternehmen / Kanzlei <span className="text-red-600">*</span>
          </label>
          <input
            id="lead-company"
            name="company"
            type="text"
            required
            autoComplete="organization"
            maxLength={200}
            onFocus={markStarted}
            onChange={clearError}
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
          />
        </div>

        <div>
          <label htmlFor="lead-segment" className="block text-xs font-semibold text-slate-700">
            Sie sind … <span className="text-red-600">*</span>
          </label>
          <select
            id="lead-segment"
            name="segment"
            required
            defaultValue=""
            onFocus={markStarted}
            onChange={clearError}
            className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
          >
            <option value="" disabled>
              Bitte wählen
            </option>
            {LEAD_SEGMENTS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="lead-message" className="block text-xs font-semibold text-slate-700">
            Nachricht (optional)
          </label>
          <textarea
            id="lead-message"
            name="message"
            rows={4}
            maxLength={4000}
            onFocus={markStarted}
            onChange={clearError}
            placeholder="z. B. gewünschtes Paket, Zeitfenster, Fragen zu SAP oder Kanzlei-Dossiers"
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
          />
        </div>

        {status === "error" && (
          <div
            className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950"
            role="alert"
            aria-live="assertive"
          >
            <p className="font-medium">Senden fehlgeschlagen.</p>
            <p className="mt-1 text-amber-900/90">
              {errorDetail === "network"
                ? "Bitte prüfen Sie Ihre Verbindung und versuchen Sie es erneut."
                : "Bitte prüfen Sie die Pflichtfelder und Ihre E-Mail-Adresse."}
            </p>
            <p className="mt-2 text-xs">
              Alternativ erreichen Sie uns direkt per E-Mail:{" "}
              <a className="font-semibold text-cyan-800 underline" href={PUBLIC_CONTACT_MAILTO}>
                {PUBLIC_CONTACT_EMAIL}
              </a>
            </p>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-3 pt-2">
          <button type="submit" disabled={status === "submitting"} className={CH_BTN_PRIMARY}>
            {status === "submitting" ? "Wird gesendet …" : "Anfrage senden"}
          </button>
          <a href={PUBLIC_CONTACT_MAILTO} className={CH_BTN_SECONDARY}>
            Stattdessen E-Mail öffnen
          </a>
        </div>
      </form>
    </div>
  );
}
