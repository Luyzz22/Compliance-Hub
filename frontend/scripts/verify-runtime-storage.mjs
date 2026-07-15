import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const errors = [];
const runtimeBoundary = readFileSync(resolve("src/lib/runtimeFileIO.ts"), "utf8");
const packageJson = JSON.parse(readFileSync(resolve("package.json"), "utf8"));
const vercelConfig = JSON.parse(readFileSync(resolve("vercel.json"), "utf8"));
const stores = [
  "advisorEvidenceHookStore.ts",
  "advisorKpiHistoryStore.ts",
  "advisorMandantHistoryStore.ts",
  "advisorMandantReminderStore.ts",
  "advisorSlaSignalStateStore.ts",
  "boardReadinessBriefingSnapshotStore.ts",
  "gtmProductAccountMapStore.ts",
  "gtmWeeklyReviewStore.ts",
  "kanzleiMonthlyReportBaseline.ts",
  "leadOpsState.ts",
  "leadPersistence.ts",
  "leadSyncStore.ts",
];

for (const dependency of ["@azure/identity", "@azure/storage-blob", "@vercel/oidc"]) {
  if (!packageJson.dependencies?.[dependency]) {
    errors.push(`package.json: ${dependency} must be a pinned runtime dependency`);
  }
}

if (JSON.stringify(vercelConfig.regions) !== JSON.stringify(["fra1"])) {
  errors.push("vercel.json: production functions must be pinned exclusively to fra1");
}
if (vercelConfig.functionFailoverRegions !== undefined) {
  errors.push("vercel.json: unreviewed cross-region function failover is forbidden");
}

for (const invariant of [
  "ClientAssertionCredential",
  "ManagedIdentityCredential",
  "getVercelOidcToken",
  "COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND must be azure_blob in production",
  "withAzureRuntimeStorageLock",
  "getBlobLeaseClient",
  "getAppendBlobClient",
]) {
  if (!runtimeBoundary.includes(invariant)) {
    errors.push(`runtimeFileIO.ts: missing required invariant ${invariant}`);
  }
}

for (const forbidden of [
  "StorageSharedKeyCredential",
  "fromConnectionString",
  "AZURE_STORAGE_CONNECTION_STRING",
  "AZURE_STORAGE_ACCOUNT_KEY",
]) {
  if (runtimeBoundary.includes(forbidden)) {
    errors.push(`runtimeFileIO.ts: long-lived Azure storage credential path ${forbidden} is forbidden`);
  }
}

for (const store of stores) {
  const path = resolve("src/lib", store);
  const source = readFileSync(path, "utf8");
  if (!source.includes('from "@/lib/runtimeFileIO"')) {
    errors.push(`${store}: must use the governed runtime storage boundary`);
  }
  if (/from ["']node:fs(?:\/promises)?["']/.test(source)) {
    errors.push(`${store}: direct filesystem access is forbidden`);
  }
}

if (errors.length) {
  process.stderr.write(`Runtime storage verification failed:\n- ${errors.join("\n- ")}\n`);
  process.exit(1);
}

process.stdout.write("Runtime storage verification passed\n");
