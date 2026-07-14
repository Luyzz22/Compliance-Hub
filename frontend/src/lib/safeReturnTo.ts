const DEFAULT_AUTHENTICATED_PATH = "/board/executive-dashboard";

export function safeReturnTo(raw: string | null): string {
  if (!raw) return DEFAULT_AUTHENTICATED_PATH;
  if (!raw.startsWith("/") || raw.startsWith("//")) {
    return DEFAULT_AUTHENTICATED_PATH;
  }
  if (/^[a-z]+:/i.test(raw)) return DEFAULT_AUTHENTICATED_PATH;
  try {
    const decoded = decodeURIComponent(raw);
    if (decoded.includes("\n") || decoded.includes("\r")) {
      return DEFAULT_AUTHENTICATED_PATH;
    }
  } catch {
    return DEFAULT_AUTHENTICATED_PATH;
  }
  return raw === "/board" ? DEFAULT_AUTHENTICATED_PATH : raw;
}
