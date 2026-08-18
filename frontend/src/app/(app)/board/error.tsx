"use client";

import { ServiceUnavailableError } from "@/components/errors/ServiceUnavailableError";

export default function BoardErrorBoundary(props: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return <ServiceUnavailableError {...props} title="Board vorübergehend nicht verfügbar" />;
}
