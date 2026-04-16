"use client";

import { useRouter } from "next/navigation";

import { CH_BTN_PRIMARY } from "@/lib/boardLayout";
import { tenantNis2WizardSessionPath } from "@/lib/nis2WizardRoutes";

interface Props {
  tenantId: string;
}

/**
 * TODO: POST /api/v1/nis2/wizard/sessions — bis dahin lokale Session-ID (UUID).
 */
export function StartNis2WizardButton({ tenantId: _tenantId }: Props) {
  const router = useRouter();

  function start() {
    const id =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `wiz-${Date.now()}`;
    router.push(tenantNis2WizardSessionPath(id));
    router.refresh();
  }

  return (
    <button type="button" className={CH_BTN_PRIMARY} onClick={start}>
      Neuen NIS2-Wizard starten
    </button>
  );
}
