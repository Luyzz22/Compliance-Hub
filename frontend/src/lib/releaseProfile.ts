export const PUBLIC_SITE_RELEASE_PROFILE = "public_site" as const;
export const ENTERPRISE_RELEASE_PROFILE = "enterprise" as const;
export const SYNTHETIC_DEMO_RELEASE_PROFILE = "synthetic_demo" as const;

export type ReleaseProfile =
  | typeof PUBLIC_SITE_RELEASE_PROFILE
  | typeof ENTERPRISE_RELEASE_PROFILE
  | typeof SYNTHETIC_DEMO_RELEASE_PROFILE
  | "development";

export function getReleaseProfile(): ReleaseProfile {
  const profile = process.env.COMPLIANCEHUB_RELEASE_PROFILE?.trim();
  if (profile === PUBLIC_SITE_RELEASE_PROFILE) return profile;
  if (profile === ENTERPRISE_RELEASE_PROFILE) return profile;
  if (profile === SYNTHETIC_DEMO_RELEASE_PROFILE) return profile;
  return "development";
}

export function isPublicSiteRelease(): boolean {
  return getReleaseProfile() === PUBLIC_SITE_RELEASE_PROFILE;
}

function enabled(name: string): boolean {
  return ["1", "true", "yes", "on"].includes(
    process.env[name]?.trim().toLowerCase() || "",
  );
}

/**
 * Password identity is permitted only for the bounded, read-only synthetic preview.
 * Normal production images continue to require Entra and reject this path.
 */
export function syntheticDemoPasswordLoginIsAllowed(): boolean {
  return (
    getReleaseProfile() === SYNTHETIC_DEMO_RELEASE_PROFILE &&
    process.env.COMPLIANCEHUB_RELEASE_CHANNEL === "pilot" &&
    enabled("COMPLIANCEHUB_FEATURE_DEMO_MODE") &&
    enabled("COMPLIANCEHUB_DEMO_BLOCK_ALL_MUTATIONS") &&
    enabled("COMPLIANCEHUB_DEMO_SYNTHETIC_ONLY_ATTESTED") &&
    enabled("COMPLIANCEHUB_PASSWORD_LOGIN_ENABLED") &&
    !enabled("COMPLIANCEHUB_SELF_REGISTRATION_ENABLED") &&
    !enabled("COMPLIANCEHUB_PUBLIC_DEMO_ENABLED") &&
    !enabled("COMPLIANCEHUB_ENTRA_ENABLED")
  );
}
