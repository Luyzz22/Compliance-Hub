"use client";

import { ServiceUnavailableError } from "@/components/errors/ServiceUnavailableError";

export default function ComplianceOverviewErrorBoundary(props: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <ServiceUnavailableError
      {...props}
      title="Compliance-Übersicht vorübergehend nicht verfügbar"
    />
  );
}
