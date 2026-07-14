import { CSRF_COOKIE_NAME } from "@/lib/authConstants";

export function browserCsrfHeaders(cookieSource?: string): Record<string, string> {
  const source = cookieSource ?? (typeof document !== "undefined" ? document.cookie : "");
  if (!source) return {};
  for (const part of source.split(";")) {
    const [rawName, ...rawValue] = part.trim().split("=");
    if (rawName !== CSRF_COOKIE_NAME) continue;
    const value = rawValue.join("=");
    if (!value) return {};
    try {
      return { "x-csrf-token": decodeURIComponent(value) };
    } catch {
      return {};
    }
  }
  return {};
}
