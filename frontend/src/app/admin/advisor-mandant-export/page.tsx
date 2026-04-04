import { AdvisorMandantExportClient } from "@/components/admin/AdvisorMandantExportClient";

export const dynamic = "force-dynamic";

export default function AdminAdvisorMandantExportPage() {
  const adminConfigured = Boolean(process.env.LEAD_ADMIN_SECRET?.trim());

  return (
    <div className="min-h-screen bg-slate-100 px-4 py-10">
      <div className="mx-auto max-w-3xl">
        <AdvisorMandantExportClient adminConfigured={adminConfigured} />
      </div>
    </div>
  );
}
