import { entraConfig } from "@/lib/entraAuth";
import { isEnterpriseProductionRuntime } from "@/lib/outboundEndpointPolicy";
import { syntheticDemoPasswordLoginIsAllowed } from "@/lib/releaseProfile";
import { noStoreJson } from "@/lib/serverSession";

export const runtime = "nodejs";

export function GET() {
  const production = isEnterpriseProductionRuntime();
  const syntheticPasswordLogin = syntheticDemoPasswordLoginIsAllowed();
  try {
    entraConfig();
    return noStoreJson({
      enabled: true,
      passwordLoginEnabled: !production || syntheticPasswordLogin,
      selfRegistrationEnabled: !production,
    });
  } catch {
    return noStoreJson({
      enabled: false,
      passwordLoginEnabled: !production || syntheticPasswordLogin,
      selfRegistrationEnabled: !production,
    });
  }
}
