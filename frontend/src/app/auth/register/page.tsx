"use client";

import Link from "next/link";
import React, { useState } from "react";

import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_SHELL,
} from "@/lib/boardLayout";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

type RegisterResult = {
  user_id: string;
  email: string;
  verification_token?: string;
};

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [company, setCompany] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RegisterResult | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          password,
          display_name: displayName || undefined,
          company: company || undefined,
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        const code = body?.detail?.code ?? body?.detail ?? "";
        if (code === "email_taken") {
          throw new Error("Diese E-Mail-Adresse ist bereits registriert.");
        }
        if (code === "weak_password") {
          throw new Error(
            "Das Passwort ist zu schwach. Mindestens 10 Zeichen, Groß-/Kleinbuchstaben und eine Zahl.",
          );
        }
        throw new Error(
          `Registrierung fehlgeschlagen (HTTP ${res.status}). Bitte versuchen Sie es erneut.`,
        );
      }

      const data: RegisterResult = await res.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unbekannter Fehler");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Identität"
        title="Registrierung"
        description="Erstellen Sie ein neues ComplianceHub-Konto."
      />

      {result ? (
        <div className={CH_CARD}>
          <h2 className="text-lg font-semibold text-emerald-700">
            Registrierung erfolgreich
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            Konto erstellt für <strong>{result.email}</strong> (ID:{" "}
            <code className="rounded bg-slate-100 px-1 text-xs">
              {result.user_id}
            </code>
            ).
          </p>
          {result.verification_token && (
            <p className="mt-2 text-sm text-slate-600">
              Verifizierungstoken:{" "}
              <code className="rounded bg-slate-100 px-1 text-xs">
                {result.verification_token}
              </code>
            </p>
          )}
          <Link href="/auth/login" className={`${CH_BTN_PRIMARY} mt-4`}>
            Zum Login
          </Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className={CH_CARD}>
          <fieldset disabled={loading} className="space-y-4">
            <div>
              <label
                htmlFor="reg-email"
                className="block text-sm font-medium text-slate-700"
              >
                E-Mail *
              </label>
              <input
                id="reg-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
              />
            </div>

            <div>
              <label
                htmlFor="reg-password"
                className="block text-sm font-medium text-slate-700"
              >
                Passwort *
              </label>
              <input
                id="reg-password"
                type="password"
                required
                minLength={10}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
              />
            </div>

            <div>
              <label
                htmlFor="reg-display-name"
                className="block text-sm font-medium text-slate-700"
              >
                Anzeigename
              </label>
              <input
                id="reg-display-name"
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
              />
            </div>

            <div>
              <label
                htmlFor="reg-company"
                className="block text-sm font-medium text-slate-700"
              >
                Unternehmen
              </label>
              <input
                id="reg-company"
                type="text"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
              />
            </div>

            {error && (
              <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </p>
            )}

            <button type="submit" className={CH_BTN_PRIMARY}>
              {loading ? "Lädt…" : "Registrieren"}
            </button>
          </fieldset>

          <p className="mt-4 text-sm text-slate-500">
            Bereits registriert?{" "}
            <Link
              href="/auth/login"
              className="font-medium text-cyan-700 underline underline-offset-2"
            >
              Zum Login
            </Link>
          </p>
        </form>
      )}
    </div>
  );
}
