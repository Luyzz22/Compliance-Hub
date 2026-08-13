import { KanzleiPortfolioCockpitClient } from "@/components/admin/KanzleiPortfolioCockpitClient";
import { leadAdminIsConfigured } from "@/lib/leadAdminAuth";

export const dynamic = "force-dynamic";

export default function AdminAdvisorPortfolioPage() {
  const adminConfigured = leadAdminIsConfigured();

  return (
    <div className="min-h-screen bg-slate-100 px-4 py-10">
      <div className="mx-auto max-w-7xl">
        <KanzleiPortfolioCockpitClient adminConfigured={adminConfigured} />
      </div>
    </div>
  );
}
