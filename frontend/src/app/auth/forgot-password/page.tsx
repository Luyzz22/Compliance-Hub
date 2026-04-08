"use client";

import Link from "next/link";
import React, { useState } from "react";

import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  CH_BTN_PRIMARY,
  CH_CARD,
  CH_SHELL,
} from "@/lib/boardLayout";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");

  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);

    try {
      await fetch(`${API_BASE_URL}/api/v1/auth/password-reset/request`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
    } catch {
      // Intentionally ignored – never reveal whether the email exists
    } finally {
      setLoading(false);
      setSubmitted(true);
    }
  }

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Identität"
        title="Passwort vergessen"
        description="Geben Sie Ihre E-Mail-Adresse ein, um einen Passwort-Reset-Link zu erhalten."
      />

      {submitted ? (
        <div className={CH_CARD}>
          <h2 className="text-lg font-semibold text-emerald-700">
            E-Mail gesendet
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            Falls ein Konto mit dieser Adresse existiert, erhalten Sie in Kürze
            eine E-Mail mit Anweisungen zum Zurücksetzen Ihres Passworts.
          </p>
          <div className="mt-4 flex gap-3">
            <Link href="/auth/login" className={CH_BTN_PRIMARY}>
              Zurück zum Login
            </Link>
            <Link
              href="/auth/reset-password"
              className="inline-flex items-center text-sm font-medium text-cyan-700 underline underline-offset-2"
            >
              Token eingeben
            </Link>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className={CH_CARD}>
          <fieldset disabled={loading} className="space-y-4">
            <div>
              <label
                htmlFor="fp-email"
                className="block text-sm font-medium text-slate-700"
              >
                E-Mail
              </label>
              <input
                id="fp-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
              />
            </div>

            <button type="submit" className={CH_BTN_PRIMARY}>
              {loading ? "Lädt…" : "Link anfordern"}
            </button>
          </fieldset>

          <p className="mt-4 text-sm text-slate-500">
            <Link
              href="/auth/login"
              className="font-medium text-cyan-700 underline underline-offset-2"
            >
              Zurück zum Login
            </Link>
          </p>
        </form>
      )}
    </div>
  );
}
