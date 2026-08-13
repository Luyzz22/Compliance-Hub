import { Suspense } from "react";

import { AdminLeadInboxClient } from "@/components/admin/AdminLeadInboxClient";
import { leadAdminIsConfigured } from "@/lib/leadAdminAuth";

export const dynamic = "force-dynamic";

export default function AdminLeadsPage() {
  const adminConfigured = leadAdminIsConfigured();

  return (
    <div className="min-h-screen bg-slate-100 px-4 py-10">
      <div className="mx-auto max-w-7xl">
        <Suspense fallback={<div className="py-16 text-center text-sm text-slate-500">Laden…</div>}>
          <AdminLeadInboxClient adminConfigured={adminConfigured} />
        </Suspense>
      </div>
    </div>
  );
}
