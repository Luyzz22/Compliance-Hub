import { entraConfig } from "@/lib/entraAuth";
import { noStoreJson } from "@/lib/serverSession";

export const runtime = "nodejs";

export function GET() {
  try {
    entraConfig();
    const production =
      process.env.VERCEL_ENV === "production" ||
      process.env.COMPLIANCEHUB_RELEASE_CHANNEL === "production";
    return noStoreJson({
      enabled: true,
      passwordLoginEnabled: !production,
    });
  } catch {
    return noStoreJson({ enabled: false, passwordLoginEnabled: true });
  }
}
