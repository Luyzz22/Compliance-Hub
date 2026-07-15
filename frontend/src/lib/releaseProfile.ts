export const PUBLIC_SITE_RELEASE_PROFILE = "public_site" as const;
export const ENTERPRISE_RELEASE_PROFILE = "enterprise" as const;

export type ReleaseProfile =
  | typeof PUBLIC_SITE_RELEASE_PROFILE
  | typeof ENTERPRISE_RELEASE_PROFILE
  | "development";

export function getReleaseProfile(): ReleaseProfile {
  const profile = process.env.COMPLIANCEHUB_RELEASE_PROFILE?.trim();
  if (profile === PUBLIC_SITE_RELEASE_PROFILE) return profile;
  if (profile === ENTERPRISE_RELEASE_PROFILE) return profile;
  return "development";
}

export function isPublicSiteRelease(): boolean {
  return getReleaseProfile() === PUBLIC_SITE_RELEASE_PROFILE;
}
