import "server-only";

import { cookies } from "next/headers";

import { SESSION_COOKIE_NAME } from "@/lib/authConstants";
import { approvedVersionedApiPath } from "@/lib/outboundEndpointPolicy";
import { complianceApiBaseUrl } from "@/lib/serverSession";

export async function serverSessionApiFetch(
  path: string,
  init?: RequestInit,
): Promise<Response> {
  const approvedPath = approvedVersionedApiPath(path);
  const token = (await cookies()).get(SESSION_COOKIE_NAME)?.value?.trim();
  if (!token) throw new Error("Authenticated server session is required");

  const headers = new Headers(init?.headers);
  headers.delete("authorization");
  headers.delete("cookie");
  headers.delete("x-api-key");
  headers.delete("x-opa-user-role");
  headers.delete("x-tenant-id");
  headers.set("Authorization", `Bearer ${token}`);

  return fetch(`${complianceApiBaseUrl()}${approvedPath}`, {
    ...init,
    headers,
    cache: "no-store",
    redirect: "manual",
    signal: AbortSignal.timeout(30_000),
  });
}
