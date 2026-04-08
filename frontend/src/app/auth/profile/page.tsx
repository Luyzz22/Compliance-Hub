"use client";

import Link from "next/link";
import React, { useCallback, useEffect, useState } from "react";

import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_SECTION_LABEL,
  CH_SHELL,
} from "@/lib/boardLayout";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const API_KEY =
  process.env.NEXT_PUBLIC_API_KEY ||
  process.env.COMPLIANCEHUB_API_KEY ||
  "tenant-overview-key";

type Role = {
  role: string;
  scope?: string;
  granted_at?: string;
};

type UserProfile = {
  user_id: string;
  email: string;
  display_name?: string;
  company?: string;
  language?: string;
  timezone?: string;
  roles?: Role[];
};

function authHeaders(): Record<string, string> {
  return {
    "Content-Type": "application/json",
    "x-api-key": API_KEY,
  };
}

export default function ProfilePage() {
  const [userId, setUserId] = useState("");
  const [profile, setProfile] = useState<UserProfile | null>(null);

  const [displayName, setDisplayName] = useState("");
  const [company, setCompany] = useState("");
  const [language, setLanguage] = useState("");
  const [timezone, setTimezone] = useState("");

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const loadProfile = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    setProfile(null);

    try {
      const res = await fetch(
        `${API_BASE_URL}/api/v1/auth/profile/${encodeURIComponent(id)}`,
        { headers: authHeaders() },
      );

      if (!res.ok) {
        throw new Error(`Profil konnte nicht geladen werden (HTTP ${res.status}).`);
      }

      const data: UserProfile = await res.json();
      setProfile(data);
      setDisplayName(data.display_name ?? "");
      setCompany(data.company ?? "");
      setLanguage(data.language ?? "de");
      setTimezone(data.timezone ?? "Europe/Berlin");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unbekannter Fehler");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get("user_id") ?? "";
    if (id) {
      setUserId(id);
      loadProfile(id);
    }
  }, [loadProfile]);

  async function handleLoadProfile(e: React.FormEvent) {
    e.preventDefault();
    if (userId.trim()) {
      await loadProfile(userId.trim());
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!profile) return;
    setSaving(true);
    setError(null);
    setSaveSuccess(false);

    try {
      const res = await fetch(
        `${API_BASE_URL}/api/v1/auth/profile/${encodeURIComponent(profile.user_id)}`,
        {
          method: "PUT",
          headers: authHeaders(),
          body: JSON.stringify({
            display_name: displayName || undefined,
            company: company || undefined,
            language: language || undefined,
            timezone: timezone || undefined,
          }),
        },
      );

      if (!res.ok) {
        throw new Error(`Profil konnte nicht gespeichert werden (HTTP ${res.status}).`);
      }

      const data: UserProfile = await res.json();
      setProfile(data);
      setSaveSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unbekannter Fehler");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Identität"
        title="Benutzerprofil"
        description="Profildaten und Rollenzuweisungen verwalten."
        actions={
          <Link href="/settings" className={CH_BTN_SECONDARY}>
            Zurück zu Einstellungen
          </Link>
        }
      />

      {/* User-ID lookup */}
      {!profile && !loading && (
        <form onSubmit={handleLoadProfile} className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Profil laden</p>
          <div className="mt-3">
            <label
              htmlFor="prof-uid"
              className="block text-sm font-medium text-slate-700"
            >
              Benutzer-ID
            </label>
            <input
              id="prof-uid"
              type="text"
              required
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="z. B. usr_abc123"
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm shadow-sm focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>
          <button type="submit" className={`${CH_BTN_PRIMARY} mt-4`}>
            Laden
          </button>
        </form>
      )}

      {loading && (
        <div className={CH_CARD}>
          <p className="text-sm text-slate-500">Lädt…</p>
        </div>
      )}

      {error && (
        <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </p>
      )}

      {profile && (
        <>
          {/* Profile info card */}
          <div className={CH_CARD}>
            <p className={CH_SECTION_LABEL}>Kontoinformationen</p>
            <dl className="mt-3 space-y-2 text-sm">
              <div className="flex gap-2">
                <dt className="font-medium text-slate-600">ID:</dt>
                <dd className="font-mono text-slate-900">{profile.user_id}</dd>
              </div>
              <div className="flex gap-2">
                <dt className="font-medium text-slate-600">E-Mail:</dt>
                <dd className="text-slate-900">{profile.email}</dd>
              </div>
            </dl>
          </div>

          {/* Edit form */}
          <form onSubmit={handleSave} className={CH_CARD}>
            <p className={CH_SECTION_LABEL}>Profil bearbeiten</p>
            <fieldset disabled={saving} className="mt-3 space-y-4">
              <div>
                <label
                  htmlFor="prof-name"
                  className="block text-sm font-medium text-slate-700"
                >
                  Anzeigename
                </label>
                <input
                  id="prof-name"
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                />
              </div>

              <div>
                <label
                  htmlFor="prof-company"
                  className="block text-sm font-medium text-slate-700"
                >
                  Unternehmen
                </label>
                <input
                  id="prof-company"
                  type="text"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                />
              </div>

              <div>
                <label
                  htmlFor="prof-lang"
                  className="block text-sm font-medium text-slate-700"
                >
                  Sprache
                </label>
                <select
                  id="prof-lang"
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                >
                  <option value="de">Deutsch</option>
                  <option value="en">English</option>
                  <option value="fr">Français</option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="prof-tz"
                  className="block text-sm font-medium text-slate-700"
                >
                  Zeitzone
                </label>
                <select
                  id="prof-tz"
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                >
                  <option value="Europe/Berlin">Europe/Berlin</option>
                  <option value="Europe/Zurich">Europe/Zurich</option>
                  <option value="Europe/Vienna">Europe/Vienna</option>
                  <option value="Europe/London">Europe/London</option>
                  <option value="UTC">UTC</option>
                </select>
              </div>

              {saveSuccess && (
                <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                  Profil erfolgreich gespeichert.
                </p>
              )}

              <button type="submit" className={CH_BTN_PRIMARY}>
                {saving ? "Speichert…" : "Speichern"}
              </button>
            </fieldset>
          </form>

          {/* Roles table */}
          {profile.roles && profile.roles.length > 0 && (
            <div className={CH_CARD}>
              <p className={CH_SECTION_LABEL}>Rollen</p>
              <div className="mt-3 overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                      <th className="pb-2 pr-4">Rolle</th>
                      <th className="pb-2 pr-4">Geltungsbereich</th>
                      <th className="pb-2">Vergeben am</th>
                    </tr>
                  </thead>
                  <tbody>
                    {profile.roles.map((r, i) => (
                      <tr
                        key={i}
                        className="border-b border-slate-100 last:border-0"
                      >
                        <td className="py-2 pr-4 font-medium text-slate-900">
                          {r.role}
                        </td>
                        <td className="py-2 pr-4 text-slate-600">
                          {r.scope ?? "–"}
                        </td>
                        <td className="py-2 text-slate-600">
                          {r.granted_at ?? "–"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
