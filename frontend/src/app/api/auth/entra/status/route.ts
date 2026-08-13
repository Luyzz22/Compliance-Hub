import { entraConfig } from "@/lib/entraAuth";
import { isEnterpriseProductionRuntime } from "@/lib/outboundEndpointPolicy";
import { noStoreJson } from "@/lib/serverSession";

export const runtime = "nodejs";

export function GET() {
  const production = isEnterpriseProductionRuntime();
  try {
    entraConfig();
    return noStoreJson({
      enabled: true,
      passwordLoginEnabled: !production,
      selfRegistrationEnabled: !production,
    });
  } catch {
    return noStoreJson({
      enabled: false,
      passwordLoginEnabled: !production,
      selfRegistrationEnabled: !production,
    });
  }
}
