import type { NextRequest } from "next/server";

import { proxyPublicIdentityMutation } from "@/lib/publicIdentityProxy";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  return proxyPublicIdentityMutation(request, "password_reset_confirm");
}
