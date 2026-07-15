"use client";

import Link from "next/link";

import { sendMarketingEvent } from "@/lib/marketingTelemetryClient";

type Props = {
  href: string;
  ctaId: string;
  quelle: string;
  className: string;
  children: React.ReactNode;
  trackingEnabled?: boolean;
};

export function TrackedContactLink({
  href,
  ctaId,
  quelle,
  className,
  children,
  trackingEnabled = true,
}: Props) {
  return (
    <Link
      href={href}
      className={className}
      prefetch={false}
      onClick={
        trackingEnabled
          ? () => sendMarketingEvent({ event: "cta_click", cta_id: ctaId, quelle })
          : undefined
      }
    >
      {children}
    </Link>
  );
}
