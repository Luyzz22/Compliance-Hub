"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import React, { Suspense, useCallback, useState } from "react";

import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_SHELL,
} from "@/lib/boardLayout";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

type LoginResult = {
  user_id: string;
  email: string;
  display_name?: string;
  access_token?: string;
};

/**
 * Validate that a `next` redirect target is safe (relative path only).
 * Blocks absolute URLs, protocol-relative URLs, and other open-redirect vectors.
 */
function safeReturnTo(raw: string | null): string {
  const fallback = "/board";
  if (!raw) return fallback;
  // Must start with "/" and must NOT start with "//" (protocol-relative)
  if (!raw.startsWith("/") || raw.startsWith("//")) return fallback;
  // Block any URL that contains a protocol-like pattern
  if (/^[a-z]+:/i.test(raw)) return fallback;
  // Block encoded characters that could be used for header injection
  try {
    const decoded = decodeURIComponent(raw);
    if (decoded.includes("\n") || decoded.includes("\r")) return fallback;
  } catch {
    return fallback;
  }
  return raw;
}

function LoginPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const returnTo = safeReturnTo(searchParams.get("next"));

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<LoginResult | null>(null);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setLoading(true);
      setError(null);
      setResult(null);

      try {
        const res = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });

        if (!res.ok) {
          const body = await res.json().catch(() => null);
          const code = body?.detail?.code ?? body?.detail ?? "";
          if (code === "invalid_credentials") {
            throw new Error("E-Mail oder Passwort ist ungültig.");
          }
          if (code === "account_locked") {
            throw new Error(
              "Ihr Konto ist gesperrt. Bitte wenden Sie sich an den Administrator.",
            );
          }
          throw new Error(
            `Anmeldung fehlgeschlagen (HTTP ${res.status}). Bitte versuchen Sie es erneut.`,
          );
        }

        const data: LoginResult = await res.json();
        setResult(data);
        // Redirect to the safe returnTo target
        router.push(returnTo);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unbekannter Fehler");
      } finally {
        setLoading(false);
      }
    },
    [email, password, returnTo, router],
  );

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Identität"
        title="Anmeldung"
        description="Melden Sie sich mit Ihrem ComplianceHub-Konto an."
      />

      {result ? (
        <div className={CH_CARD}>
          <h2 className="text-lg font-semibold text-emerald-700">
            Anmeldung erfolgreich
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            Willkommen{result.display_name ? `, ${result.display_name}` : ""}!
            Sie werden zum Dashboard weitergeleitet.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Link href={returnTo} className={CH_BTN_PRIMARY}>
              Weiter
            </Link>
            <Link href="/tenant/compliance-overview" className={CH_BTN_SECONDARY}>
              Zum Workspace
            </Link>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className={CH_CARD}>
          <fieldset disabled={loading} className="space-y-4">
            <div>
              <label
                htmlFor="login-email"
                className="block text-sm font-medium text-slate-700"
              >
                E-Mail
              </label>
              <input
                id="login-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
              />
            </div>

            <div>
              <label
                htmlFor="login-password"
                className="block text-sm font-medium text-slate-700"
              >
                Passwort
              </label>
              <input
                id="login-password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
              />
            </div>

            {error && (
              <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </p>
            )}

            <button type="submit" className={CH_BTN_PRIMARY}>
              {loading ? "Lädt…" : "Anmelden"}
            </button>
          </fieldset>

          <div className="mt-4 flex flex-col gap-1 text-sm text-slate-500">
            <p>
              <Link
                href="/auth/forgot-password"
                className="font-medium text-cyan-700 underline underline-offset-2"
              >
                Passwort vergessen?
              </Link>
            </p>
            <p>
              Noch kein Konto?{" "}
              <Link
                href="/auth/register"
                className="font-medium text-cyan-700 underline underline-offset-2"
              >
                Jetzt registrieren
              </Link>
            </p>
          </div>
        </form>
      )}
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginPageInner />
    </Suspense>
  );
}
