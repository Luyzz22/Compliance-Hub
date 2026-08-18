"use client";

import { ServiceUnavailableError } from "@/components/errors/ServiceUnavailableError";

export default function AdvisorErrorBoundary(props: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return <ServiceUnavailableError {...props} title="Advisor-Bereich vorübergehend nicht verfügbar" />;
}
