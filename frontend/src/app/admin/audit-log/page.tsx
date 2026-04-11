import { AuditLogClient } from "@/components/admin/AuditLogClient";

export const dynamic = "force-dynamic";

export default function AdminAuditLogPage() {
  return (
    <div className="min-h-screen bg-slate-100 px-4 py-10">
      <div className="mx-auto max-w-7xl">
        <AuditLogClient />
      </div>
    </div>
  );
}
