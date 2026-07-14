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
import { safeReturnTo } from "@/lib/safeReturnTo";

type LoginResult = {
  ok: true;
  user: {
    user_id: string;
    email: string;
    display_name?: string | null;
    tenant_id: string;
    role: string;
  };
};

type LoginFailure = {
  ok?: false;
  error?: string;
  detail?: { code?: string; message?: string; tenants?: string[] } | string;
};

function LoginPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const returnTo = safeReturnTo(searchParams.get("next"));

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tenantId, setTenantId] = useState("");
  const [tenantOptions, setTenantOptions] = useState<string[]>([]);

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
        const res = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({
            email,
            password,
            ...(tenantId ? { tenant_id: tenantId } : {}),
          }),
        });

        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as LoginFailure | null;
          const detail = body?.detail;
          const code = typeof detail === "object" ? detail?.code : detail;
          if (code === "tenant_selection_required" && typeof detail === "object") {
            const tenants = detail.tenants ?? [];
            setTenantOptions(tenants);
            setTenantId(tenants[0] ?? "");
            throw new Error("Bitte wählen Sie den Mandanten für diese Sitzung aus.");
          }
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
        router.replace(returnTo);
        router.refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unbekannter Fehler");
      } finally {
        setLoading(false);
      }
    },
    [email, password, returnTo, router, tenantId],
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
            Willkommen
            {result.user.display_name ? `, ${result.user.display_name}` : ""}!
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

            {tenantOptions.length > 0 && (
              <div>
                <label
                  htmlFor="login-tenant"
                  className="block text-sm font-medium text-slate-700"
                >
                  Mandant
                </label>
                <select
                  id="login-tenant"
                  required
                  value={tenantId}
                  onChange={(event) => setTenantId(event.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                >
                  {tenantOptions.map((tenant) => (
                    <option key={tenant} value={tenant}>
                      {tenant}
                    </option>
                  ))}
                </select>
              </div>
            )}

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
