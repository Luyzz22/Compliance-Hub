const HOST_PREFIX = process.env.NODE_ENV === "production" ? "__Host-" : "";

export const SESSION_COOKIE_NAME = `${HOST_PREFIX}ch_session`;
export const CSRF_COOKIE_NAME = `${HOST_PREFIX}ch_csrf`;
export const ENTRA_TRANSACTION_COOKIE_NAME = `${HOST_PREFIX}ch_entra_tx`;

export const PROTECTED_APP_PREFIXES = [
  "/admin",
  "/advisor",
  "/app",
  "/board",
  "/internal",
  "/onboarding",
  "/settings",
  "/tenant",
  "/tenants",
] as const;

export function isProtectedAppPath(pathname: string): boolean {
  return PROTECTED_APP_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}
