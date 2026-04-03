"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useEffect } from "react";

import { tryCaptureUtmFromSearchParams } from "@/lib/attributionSessionClient";

/**
 * Legt bei erstem Auftreten von utm_* in der Tab-Session einen sessionStorage-Eintrag an.
 * Keine Cookies; kein Cross-Site-Tracking.
 */
export function SessionAttributionCapture() {
  const pathname = usePathname() ?? "/";
  const sp = useSearchParams();

  useEffect(() => {
    tryCaptureUtmFromSearchParams(sp, pathname);
  }, [pathname, sp]);

  return null;
}
