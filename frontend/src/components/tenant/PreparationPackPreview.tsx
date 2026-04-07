"use client";

import { useState } from "react";

type Props = {
  markdown: string;
};

export function PreparationPackPreview({ markdown }: Props) {
  const [copied, setCopied] = useState(false);

  async function onCopy() {
    await navigator.clipboard.writeText(markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">
          Markdown Preview
        </p>
        <button
          type="button"
          onClick={() => void onCopy()}
          className="rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 hover:bg-slate-100"
        >
          {copied ? "Kopiert" : "Markdown kopieren"}
        </button>
      </div>
      <pre className="max-h-80 overflow-auto whitespace-pre-wrap text-xs text-slate-700">
        {markdown}
      </pre>
    </div>
  );
}
