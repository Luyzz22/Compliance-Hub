import Link from "next/link";
import React from "react";

export function SbsFooter() {
  const y = new Date().getFullYear();
  return (
    <footer className="sbs-footer-2026">
      <div className="sbs-footer-inner">
        <div>
          © {y} Compliance Hub · Enterprise GRC für den DACH-Markt ·{" "}
          <span style={{ color: "var(--sbs-text-muted)" }}>
            Design angelehnt an{" "}
            <a
              href="https://sbsdeutschland.com/sbshomepage/"
              target="_blank"
              rel="noopener noreferrer"
            >
              SBS Deutschland
            </a>
          </span>
        </div>
        <div style={{ display: "flex", gap: "1rem" }}>
          <Link href="/">Start</Link>
          <Link href="/board/kpis">Board</Link>
          <Link href="/tenant/compliance-overview">Tenant</Link>
        </div>
      </div>
    </footer>
  );
}
