import { BoardReportsWorkspaceClient } from "@/components/governance/BoardReportsWorkspaceClient";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

interface Props {
  params: Promise<{ reportId: string }>;
}

export default async function TenantBoardReportDetailPage({ params }: Props) {
  const { reportId } = await params;
  const tenantId = await getWorkspaceTenantIdServer();
  return <BoardReportsWorkspaceClient tenantId={tenantId} reportId={reportId} />;
}
