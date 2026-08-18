import { BoardReadinessClient } from "@/components/admin/BoardReadinessClient";
import { leadAdminIsConfigured } from "@/lib/leadAdminAuth";

export const dynamic = "force-dynamic";

export default function AdminBoardReadinessPage() {
  const adminConfigured = leadAdminIsConfigured();

  return (
    <div className="min-h-screen bg-slate-100 px-4 py-10">
      <div className="mx-auto max-w-7xl">
        <BoardReadinessClient adminConfigured={adminConfigured} />
      </div>
    </div>
  );
}
