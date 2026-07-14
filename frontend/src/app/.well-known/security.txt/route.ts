const SECURITY_TXT = `Contact: https://complywithai.de/kontakt
Expires: 2027-07-01T00:00:00.000Z
Preferred-Languages: de, en
Canonical: https://complywithai.de/.well-known/security.txt
Policy: https://complywithai.de/trust-center
`;

export function GET(): Response {
  return new Response(SECURITY_TXT, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
