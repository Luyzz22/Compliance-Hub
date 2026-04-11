"use client";

/**
 * Client-side hook that exposes the current user role.
 *
 * The role string comes from NEXT_PUBLIC_OPA_USER_ROLE env var (same value
 * sent as x-opa-user-role header on API calls).  The hook deliberately keeps
 * things simple – no server round-trip – because server-side guards remain
 * the authoritative enforcement layer (Defense in Depth).
 */

export type UserRole =
  | "viewer"
  | "contributor"
  | "editor"
  | "auditor"
  | "compliance_officer"
  | "ciso"
  | "board_member"
  | "compliance_admin"
  | "tenant_admin"
  | "super_admin";

const ADMIN_ROLES: ReadonlySet<string> = new Set<UserRole>([
  "tenant_admin",
  "compliance_admin",
  "super_admin",
]);

const REPORTING_ROLES: ReadonlySet<string> = new Set<UserRole>([
  "board_member",
  "ciso",
  "compliance_admin",
  "tenant_admin",
  "auditor",
  "super_admin",
]);

const AI_SYSTEMS_ROLES: ReadonlySet<string> = new Set<UserRole>([
  "ciso",
  "compliance_admin",
  "compliance_officer",
  "tenant_admin",
  "board_member",
  "super_admin",
]);

const VALID_ROLES: ReadonlySet<string> = new Set<UserRole>([
  "viewer",
  "contributor",
  "editor",
  "auditor",
  "compliance_officer",
  "ciso",
  "board_member",
  "compliance_admin",
  "tenant_admin",
  "super_admin",
]);

function resolveRole(): UserRole | null {
  const raw =
    typeof window !== "undefined"
      ? process.env.NEXT_PUBLIC_OPA_USER_ROLE?.trim().toLowerCase() ?? null
      : null;
  if (!raw || !VALID_ROLES.has(raw)) return null;
  return raw as UserRole;
}

export function useUserRole(): UserRole | null {
  return resolveRole();
}

/** True when the current role is allowed to see Admin nav items. */
export function useCanSeeAdmin(): boolean {
  const role = resolveRole();
  if (!role) return true; // unauthenticated / no role → show everything (public site)
  return ADMIN_ROLES.has(role);
}

/** True when the current role is allowed to see Reporting nav items. */
export function useCanSeeReporting(): boolean {
  const role = resolveRole();
  if (!role) return true;
  return REPORTING_ROLES.has(role);
}

/** True when the current role is allowed to see AI Systems link. */
export function useCanSeeAiSystems(): boolean {
  const role = resolveRole();
  if (!role) return true;
  return AI_SYSTEMS_ROLES.has(role);
}
