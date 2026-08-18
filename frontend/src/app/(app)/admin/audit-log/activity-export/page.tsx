import { AuditActivityExportClient } from "@/components/admin/AuditActivityExportClient";

export const dynamic = "force-dynamic";

export default function AuditActivityExportPage() {
  return (
    <div className="min-h-screen bg-slate-100 px-4 py-10">
      <div className="mx-auto max-w-7xl">
        <AuditActivityExportClient />
      </div>
    </div>
  );
}
