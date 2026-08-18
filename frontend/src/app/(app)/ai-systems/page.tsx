import { redirect } from "next/navigation";

/** Einstieg ohne /tenant-Prefix: leitet zum mandantenbezogenen KI-Register weiter. */
export default function AiSystemsEntryPage() {
  redirect("/tenant/ai-systems");
}
