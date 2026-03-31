import React from "react";

const DOC_URL_RAW = process.env.NEXT_PUBLIC_DEMO_DOCS_URL?.trim();
const DOC_URL = DOC_URL_RAW && DOC_URL_RAW.length > 0 ? DOC_URL_RAW : null;

export function DemoEnvironmentBanner({ visible }: { visible: boolean }) {
  if (!visible) {
    return null;
  }
  return (
    <div
      className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-sm text-amber-950"
      role="status"
    >
      <span className="font-medium">Demo-Umgebung</span>
      <span className="text-amber-900/90">
        {" "}
        – Änderungen werden regelmäßig zurückgesetzt. Keine produktiven oder personenbezogenen Daten
        verwenden.
      </span>
      {DOC_URL ? (
        <>
          {" "}
          <a
            href={DOC_URL}
            className="font-medium text-amber-900 underline decoration-amber-600/80 underline-offset-2 hover:text-amber-950"
            target="_blank"
            rel="noreferrer"
          >
            Mehr zur Demo
          </a>
        </>
      ) : null}
    </div>
  );
}
