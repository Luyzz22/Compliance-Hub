"use client";

import { useEffect, useState } from "react";

type IdentityCapabilities = {
  passwordLoginEnabled: boolean;
  selfRegistrationEnabled: boolean;
};

export function useIdentityCapabilities(): IdentityCapabilities | null {
  const [capabilities, setCapabilities] = useState<IdentityCapabilities | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/auth/entra/status", {
      cache: "no-store",
      credentials: "same-origin",
      signal: controller.signal,
    })
      .then(async (response) => {
        const body = (await response.json().catch(() => null)) as Partial<IdentityCapabilities> | null;
        setCapabilities({
          passwordLoginEnabled: response.ok && body?.passwordLoginEnabled === true,
          selfRegistrationEnabled: response.ok && body?.selfRegistrationEnabled === true,
        });
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setCapabilities({
            passwordLoginEnabled: false,
            selfRegistrationEnabled: false,
          });
        }
      });
    return () => controller.abort();
  }, []);

  return capabilities;
}
