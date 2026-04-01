import { AdminLeadInboxClient } from "@/components/admin/AdminLeadInboxClient";

export const dynamic = "force-dynamic";

export default function AdminLeadsPage() {
  const adminConfigured = Boolean(process.env.LEAD_ADMIN_SECRET?.trim());

  return (
    <div className="min-h-screen bg-slate-100 px-4 py-10">
      <div className="mx-auto max-w-7xl">
        <AdminLeadInboxClient adminConfigured={adminConfigured} />
      </div>
    </div>
  );
}
