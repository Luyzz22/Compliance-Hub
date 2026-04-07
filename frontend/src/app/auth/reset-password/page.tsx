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

export default function ResetPasswordPage() {
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const res = await fetch(
        `${API_BASE_URL}/api/v1/auth/password-reset/confirm`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token, new_password: newPassword }),
        },
      );

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        const code = body?.detail?.code ?? body?.detail ?? "";
        if (code === "invalid_token") {
          throw new Error(
            "Der Token ist ungültig. Bitte fordern Sie einen neuen Reset-Link an.",
          );
        }
        if (code === "token_expired") {
          throw new Error(
            "Der Token ist abgelaufen. Bitte fordern Sie einen neuen Reset-Link an.",
          );
        }
        throw new Error(
          `Passwort-Reset fehlgeschlagen (HTTP ${res.status}). Bitte versuchen Sie es erneut.`,
        );
      }

      setSuccess(true);
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
        title="Passwort zurücksetzen"
        description="Geben Sie den Reset-Token und Ihr neues Passwort ein."
      />

      {success ? (
        <div className={CH_CARD}>
          <h2 className="text-lg font-semibold text-emerald-700">
            Passwort erfolgreich geändert
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            Ihr Passwort wurde zurückgesetzt. Sie können sich jetzt mit Ihrem
            neuen Passwort anmelden.
          </p>
          <Link href="/auth/login" className={`${CH_BTN_PRIMARY} mt-4`}>
            Zum Login
          </Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className={CH_CARD}>
          <fieldset disabled={loading} className="space-y-4">
            <div>
              <label
                htmlFor="rp-token"
                className="block text-sm font-medium text-slate-700"
              >
                Reset-Token *
              </label>
              <input
                id="rp-token"
                type="text"
                required
                value={token}
                onChange={(e) => setToken(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm shadow-sm focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
              />
            </div>

            <div>
              <label
                htmlFor="rp-password"
                className="block text-sm font-medium text-slate-700"
              >
                Neues Passwort *
              </label>
              <input
                id="rp-password"
                type="password"
                required
                minLength={8}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
              />
            </div>

            {error && (
              <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </p>
            )}

            <button type="submit" className={CH_BTN_PRIMARY}>
              {loading ? "Lädt…" : "Passwort zurücksetzen"}
            </button>
          </fieldset>

          <p className="mt-4 text-sm text-slate-500">
            <Link
              href="/auth/forgot-password"
              className="font-medium text-cyan-700 underline underline-offset-2"
            >
              Neuen Token anfordern
            </Link>
          </p>
        </form>
      )}
    </div>
  );
}
