const SIX_MONTHS_MS = 183 * 24 * 60 * 60 * 1_000;

export const dynamic = "force-dynamic";

export function GET(): Response {
  const contact =
    process.env.COMPLIANCEHUB_SECURITY_CONTACT?.trim() ||
    "https://complywithai.de/kontakt";
  const expires = new Date(Date.now() + SIX_MONTHS_MS).toISOString();
  const body = [
    `Contact: ${contact}`,
    `Expires: ${expires}`,
    "Preferred-Languages: de, en",
    "Canonical: https://complywithai.de/.well-known/security.txt",
    "Policy: https://complywithai.de/trust-center#disclosure",
    "",
  ].join("\n");

  return new Response(body, {
    status: 200,
    headers: {
      "Cache-Control": "public, max-age=86400",
      "Content-Type": "text/plain; charset=utf-8",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
