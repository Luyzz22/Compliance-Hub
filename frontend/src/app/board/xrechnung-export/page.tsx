"use client";

import React, { useState } from "react";
import Link from "next/link";
import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";

import { useWorkspaceTenantIdClient } from "@/hooks/useWorkspaceTenantIdClient";
import { tenantRequestHeaders } from "@/lib/api";
import {
  CH_BTN_PRIMARY,
  CH_CARD,
  CH_PAGE_NAV_LINK,
  CH_SECTION_LABEL,
} from "@/lib/boardLayout";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.COMPLIANCEHUB_API_BASE_URL ||
  "http://localhost:8000";

interface LineItem {
  description: string;
  quantity: number;
  unit_price: number;
  tax_percent: number;
}

export default function XRechnungExportPage() {
  const workspaceTenantId = useWorkspaceTenantIdClient();
  const today = new Date().toISOString().slice(0, 10);
  const dueDateDefault = new Date(Date.now() + 30 * 86400_000)
    .toISOString()
    .slice(0, 10);

  const [invoiceId, setInvoiceId] = useState("INV-2026-001");
  const [issueDate, setIssueDate] = useState(today);
  const [dueDate, setDueDate] = useState(dueDateDefault);
  const [sellerName, setSellerName] = useState("ComplianceHub GmbH");
  const [sellerTaxId, setSellerTaxId] = useState("DE123456789");
  const [sellerAddress, setSellerAddress] = useState(
    "Musterstraße 1, 10115 Berlin",
  );
  const [buyerName, setBuyerName] = useState("");
  const [buyerReference, setBuyerReference] = useState("");
  const [buyerAddress, setBuyerAddress] = useState("");
  const [lineItems, setLineItems] = useState<LineItem[]>([
    { description: "GRC-Beratung", quantity: 1, unit_price: 0, tax_percent: 19 },
  ]);
  const [note, setNote] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  function addLineItem() {
    setLineItems([
      ...lineItems,
      { description: "", quantity: 1, unit_price: 0, tax_percent: 19 },
    ]);
  }

  function updateLineItem(idx: number, field: keyof LineItem, value: string) {
    const updated = [...lineItems];
    if (field === "description") {
      updated[idx] = { ...updated[idx], description: value };
    } else {
      updated[idx] = { ...updated[idx], [field]: parseFloat(value) || 0 };
    }
    setLineItems(updated);
  }

  function removeLineItem(idx: number) {
    setLineItems(lineItems.filter((_, i) => i !== idx));
  }

  async function handleExport() {
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const headers = tenantRequestHeaders(workspaceTenantId, undefined, { json: true });

      const body = {
        invoice_id: invoiceId,
        issue_date: issueDate,
        due_date: dueDate,
        seller_name: sellerName,
        seller_tax_id: sellerTaxId,
        seller_address: sellerAddress,
        buyer_name: buyerName,
        buyer_reference: buyerReference,
        buyer_address: buyerAddress,
        line_items: lineItems,
        currency: "EUR",
        note: note || undefined,
      };

      const res = await fetch(
        `${API_BASE_URL}/api/v1/enterprise/xrechnung/export`,
        { method: "POST", headers, body: JSON.stringify(body) },
      );

      if (res.status === 403) {
        setError(
          "Zugriff verweigert — XRechnung-Export erfordert TENANT_ADMIN oder COMPLIANCE_ADMIN Rolle.",
        );
        return;
      }
      if (res.status === 422) {
        const detail = await res.json();
        setError(
          `Validierungsfehler: ${JSON.stringify(detail.detail?.validation_errors ?? detail.detail)}`,
        );
        return;
      }
      if (!res.ok) {
        setError(`Export fehlgeschlagen (HTTP ${res.status})`);
        return;
      }

      const xml = await res.text();
      const blob = new Blob([xml], { type: "application/xml" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `XRechnung_${invoiceId}.xml`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setSuccess(true);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Export fehlgeschlagen",
      );
    } finally {
      setLoading(false);
    }
  }

  const netTotal = lineItems.reduce(
    (s, i) => s + i.quantity * i.unit_price,
    0,
  );
  const taxTotal = lineItems.reduce(
    (s, i) => s + i.quantity * i.unit_price * (i.tax_percent / 100),
    0,
  );

  return (
    <div className="min-w-0">
      <EnterprisePageHeader
        eyebrow="Reporting"
        title="XRechnung 3.0 Export"
        description="EU-konforme E-Rechnung nach XRechnung 3.0 / EN-16931 (UBL 2.1) für Rechnungen an öffentliche Auftraggeber (ERechV)."
        below={
          <>
            <Link href="/board/executive-dashboard" className={CH_PAGE_NAV_LINK}>
              Executive Dashboard
            </Link>
            <Link href="/board/datev-export" className={CH_PAGE_NAV_LINK}>
              DATEV Export
            </Link>
          </>
        }
      />

      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}
      {success && (
        <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          XRechnung erfolgreich exportiert und heruntergeladen.
        </div>
      )}

      {/* ── Seller / Buyer ── */}
      <section className={`${CH_CARD} mb-6 space-y-4`}>
        <p className={CH_SECTION_LABEL}>Rechnungsdaten</p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <label className="block text-sm">
            <span className="text-slate-600">Rechnungsnummer</span>
            <input
              type="text"
              value={invoiceId}
              onChange={(e) => setInvoiceId(e.target.value)}
              className="mt-1 block w-full rounded-lg border px-3 py-2 text-sm"
            />
          </label>
          <label className="block text-sm">
            <span className="text-slate-600">Rechnungsdatum</span>
            <input
              type="date"
              value={issueDate}
              onChange={(e) => setIssueDate(e.target.value)}
              className="mt-1 block w-full rounded-lg border px-3 py-2 text-sm"
            />
          </label>
          <label className="block text-sm">
            <span className="text-slate-600">Fälligkeitsdatum</span>
            <input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="mt-1 block w-full rounded-lg border px-3 py-2 text-sm"
            />
          </label>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <p className="mb-2 text-xs font-semibold uppercase text-slate-500">
              Verkäufer
            </p>
            <input
              type="text"
              placeholder="Name"
              value={sellerName}
              onChange={(e) => setSellerName(e.target.value)}
              className="mb-2 block w-full rounded-lg border px-3 py-2 text-sm"
            />
            <input
              type="text"
              placeholder="USt-IdNr."
              value={sellerTaxId}
              onChange={(e) => setSellerTaxId(e.target.value)}
              className="mb-2 block w-full rounded-lg border px-3 py-2 text-sm"
            />
            <input
              type="text"
              placeholder="Adresse"
              value={sellerAddress}
              onChange={(e) => setSellerAddress(e.target.value)}
              className="block w-full rounded-lg border px-3 py-2 text-sm"
            />
          </div>
          <div>
            <p className="mb-2 text-xs font-semibold uppercase text-slate-500">
              Käufer
            </p>
            <input
              type="text"
              placeholder="Name *"
              value={buyerName}
              onChange={(e) => setBuyerName(e.target.value)}
              className="mb-2 block w-full rounded-lg border px-3 py-2 text-sm"
            />
            <input
              type="text"
              placeholder="Leitweg-ID *"
              value={buyerReference}
              onChange={(e) => setBuyerReference(e.target.value)}
              className="mb-2 block w-full rounded-lg border px-3 py-2 text-sm"
            />
            <input
              type="text"
              placeholder="Adresse"
              value={buyerAddress}
              onChange={(e) => setBuyerAddress(e.target.value)}
              className="block w-full rounded-lg border px-3 py-2 text-sm"
            />
          </div>
        </div>
      </section>

      {/* ── Line Items ── */}
      <section className={`${CH_CARD} mb-6 space-y-4`}>
        <p className={CH_SECTION_LABEL}>Positionen</p>
        {lineItems.map((item, idx) => (
          <div key={idx} className="grid grid-cols-5 gap-2 items-end">
            <input
              type="text"
              placeholder="Beschreibung"
              value={item.description}
              onChange={(e) => updateLineItem(idx, "description", e.target.value)}
              className="col-span-2 rounded-lg border px-3 py-2 text-sm"
            />
            <input
              type="number"
              placeholder="Menge"
              value={item.quantity}
              onChange={(e) => updateLineItem(idx, "quantity", e.target.value)}
              className="rounded-lg border px-3 py-2 text-sm"
              min={1}
            />
            <input
              type="number"
              placeholder="Preis €"
              value={item.unit_price}
              onChange={(e) => updateLineItem(idx, "unit_price", e.target.value)}
              className="rounded-lg border px-3 py-2 text-sm"
              min={0}
              step={0.01}
            />
            <button
              type="button"
              onClick={() => removeLineItem(idx)}
              className="rounded-lg border border-red-200 px-3 py-2 text-sm text-red-600 hover:bg-red-50"
            >
              ✕
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={addLineItem}
          className="text-sm text-cyan-700 hover:underline"
        >
          + Position hinzufügen
        </button>
        <div className="text-sm text-slate-600">
          Netto: {netTotal.toFixed(2)} € · MwSt: {taxTotal.toFixed(2)} € ·{" "}
          <strong>Brutto: {(netTotal + taxTotal).toFixed(2)} €</strong>
        </div>
      </section>

      {/* ── Note ── */}
      <section className={`${CH_CARD} mb-6`}>
        <label className="block text-sm">
          <span className={CH_SECTION_LABEL}>Bemerkung (optional)</span>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            className="mt-2 block w-full rounded-lg border px-3 py-2 text-sm"
          />
        </label>
      </section>

      {/* ── Export ── */}
      <button
        onClick={handleExport}
        disabled={loading || !buyerName || !buyerReference || lineItems.length === 0}
        className={CH_BTN_PRIMARY}
      >
        {loading ? "Wird generiert…" : "📋 XRechnung 3.0 XML exportieren"}
      </button>

      {/* ── Info Box ── */}
      <section className={`${CH_CARD} mt-6 space-y-2`}>
        <p className={CH_SECTION_LABEL}>Hinweise</p>
        <ul className="list-inside list-disc space-y-1 text-sm text-slate-600">
          <li>Format: XRechnung 3.0 / EN-16931 (UBL 2.1)</li>
          <li>
            Leitweg-ID erforderlich für Rechnungen an öffentliche
            Auftraggeber
          </li>
          <li>
            Validierung gemäß Schematron-Regeln vor Download
          </li>
          <li>
            PEPPOL-Routing (AS4) ist vorbereitet
          </li>
          <li>
            Alle Exports werden im Audit-Log protokolliert
          </li>
        </ul>
      </section>
    </div>
  );
}
