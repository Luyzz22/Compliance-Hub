"use client";

import Link from "next/link";

import { sendMarketingEvent } from "@/lib/marketingTelemetryClient";

type Props = {
  href: string;
  ctaId: string;
  quelle: string;
  className: string;
  children: React.ReactNode;
};

export function TrackedContactLink({ href, ctaId, quelle, className, children }: Props) {
  return (
    <Link
      href={href}
      className={className}
      prefetch={false}
      onClick={() =>
        sendMarketingEvent({ event: "cta_click", cta_id: ctaId, quelle })
      }
    >
      {children}
    </Link>
  );
}
