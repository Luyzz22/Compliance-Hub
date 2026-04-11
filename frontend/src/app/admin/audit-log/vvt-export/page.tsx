import { VVTExportClient } from "@/components/admin/VVTExportClient";

export const dynamic = "force-dynamic";

export default function VVTExportPage() {
  return (
    <div className="min-h-screen bg-slate-100 px-4 py-10">
      <div className="mx-auto max-w-7xl">
        <VVTExportClient />
      </div>
    </div>
  );
}
