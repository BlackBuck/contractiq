"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Cross } from "lucide-react";

interface FieldScore {
  value: string | number | null;
  confidence: number;
  missing?: boolean;
}

// Backend shape: includes fields like party_identification, account_information, etc.
interface BackendContractData {
  party_identification?: any;
  account_information?: any;
  financial_details?: any;
  payment_structure?: any;
  revenue_classification?: any;
  service_level_agreements?: any;
  confidence_scores?: Record<string, number>;
  gaps?: string[];
  score?: number;
}

interface ContractDetailProps {
  // Pass backend JSON directly
  data: BackendContractData | null;
  fullPage?: boolean;
  loading: boolean;
  onClose: () => void;
  contractId?: string | null;
}

const ContractDetail: React.FC<ContractDetailProps> = ({
  data,
  loading,
  onClose,
  contractId,
  fullPage,
}) => {
  if (loading)
    return <div className="p-8 text-center">Loading contract details...</div>;
  if (!data) return null;

  // Helper: convert backend field value into FieldScore[] using the confidence for the section
  const buildFieldScores = (
    fieldValue: any,
    confidence: number | undefined
  ): FieldScore[] => {
    // Normalize confidence: accept 0-1 or 0-100
    let confVal = confidence ?? 0;
    let confPct = 0;
    if (confVal > 1) {
      confPct = Math.round(confVal);
    } else {
      confPct = Math.round(confVal * 100);
    }

    // Treat null/empty structures as missing
    const isEmptyObject =
      typeof fieldValue === "object" &&
      !Array.isArray(fieldValue) &&
      Object.keys(fieldValue || {}).length === 0;
    const isEmptyArray = Array.isArray(fieldValue) && fieldValue.length === 0;
    if (fieldValue == null || isEmptyObject || isEmptyArray) {
      return [{ value: null, confidence: confPct, missing: true }];
    }

    // If it's a dict/object, show its entries
    if (typeof fieldValue === "object" && !Array.isArray(fieldValue)) {
      return Object.entries(fieldValue).map(([k, v]) => ({
        value: `${k}: ${
          typeof v === "object" ? JSON.stringify(v, null, 2) : String(v)
        }`,
        confidence: confPct,
      }));
    }
    // If it's an array, list items
    if (Array.isArray(fieldValue)) {
      return fieldValue.map((v) => ({ value: String(v), confidence: confPct }));
    }
    // primitive
    return [{ value: String(fieldValue), confidence: confPct }];
  };

  const renderSection = (title: string, fields: FieldScore[]) => (
    <div className="mb-4">
      <h3 className="font-semibold mb-2">{title}</h3>
      <ul className="space-y-1">
        {fields.map((f, i) => (
          <li key={i} className={f.missing ? "text-red-500" : ""}>
            {f.value ? (
              // if value is multi-line JSON, show preformatted
              typeof f.value === "string" &&
              (f.value.startsWith("{") ||
                f.value.startsWith("[") ||
                f.value.includes("\n")) ? (
                <pre className="whitespace-pre-wrap text-sm bg-gray-100 p-2 rounded">
                  {f.value}
                </pre>
              ) : (
                <span>{f.value}</span>
              )
            ) : (
              <span className="italic">Missing</span>
            )}{" "}
            <div className="inline-block align-middle ml-2">
              <div className="w-24 h-2 bg-gray-200 rounded overflow-hidden">
                <div
                  className="h-2 bg-green-400"
                  style={{ width: `${f.confidence}%` }}
                />
              </div>
              <div className="text-xs text-gray-400">{f.confidence ?? 0}%</div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
  // Map backend fields -> UI sections and confidence keys
  const conf = data.confidence_scores || {};
  // Normalize/confidence fallback: if all category confidences are missing/zero,
  // distribute overall score across categories so UI can show meaningful values.
  const categoryKeys = [
    "financial_completeness",
    "party_identification",
    "payment_terms_clarity",
    "sla_definition",
    "contact_information",
  ];
  const rawScore = data.score ?? 0;
  const rawScoreFrac = rawScore > 1 ? rawScore / 100 : rawScore; // 0-1
  const providedSum = categoryKeys.reduce(
    (s, k) => s + (conf[k] ? (conf[k] > 1 ? conf[k] / 100 : conf[k]) : 0),
    0
  );
  const normalizedConf: Record<string, number> = {};
  if (providedSum === 0 && rawScoreFrac > 0) {
    // assign overall score fraction to each category as fallback
    categoryKeys.forEach((k) => (normalizedConf[k] = rawScoreFrac));
  } else {
    categoryKeys.forEach((k) => {
      const v = conf[k];
      if (v == null) normalizedConf[k] = 0;
      else normalizedConf[k] = v > 1 ? v / 100 : v;
    });
  }
  const parties = buildFieldScores(
    data.party_identification,
    normalizedConf["party_identification"]
  );
  const account_info = buildFieldScores(
    data.account_information,
    normalizedConf["contact_information"]
  );
  const financial_details = buildFieldScores(
    data.financial_details,
    normalizedConf["financial_completeness"]
  );
  const payment_structure = buildFieldScores(
    data.payment_structure,
    normalizedConf["payment_terms_clarity"]
  );
  const revenue_classification = buildFieldScores(
    data.revenue_classification,
    undefined
  );
  const sla = buildFieldScores(
    data.service_level_agreements,
    conf["sla_definition"]
  );
  const gaps = data.gaps || [];
  // Normalize total score: accept backend 0-100 or 0-1. If backend score missing, derive from normalizedConf average.
  const backendRawScore = data.score ?? 0;
  let total_score =
    backendRawScore > 1
      ? Math.round(backendRawScore)
      : Math.round(backendRawScore * 100);
  if (!total_score) {
    // derive as average of category confidences if backend score absent
    const avg =
      Object.values(normalizedConf).reduce((s, v) => s + v, 0) /
        Object.keys(normalizedConf).length || 0;
    total_score = Math.round(avg * 100);
  }

  const containerClass = fullPage
    ? "bg-white text-gray-900 rounded-lg shadow-lg p-8 max-w-4xl w-full relative z-20 ml-0"
    : "bg-white text-gray-900 rounded-lg shadow-lg p-8 max-w-2xl w-full relative z-20 ml-0";

  // mount animation state
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

  const panelAnimation = `transition-all duration-200 ease-out ${
    mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2"
  }`;

  return (
    <section className="pl-56 my-6" aria-label="Contract Details">
      <div className={`${containerClass} ${panelAnimation}`} role="region">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">Contract Details</h2>
          <button
            className="text-gray-500 hover:text-gray-800 ml-4"
            onClick={onClose}
            aria-label="Close contract details">
            <Cross />
          </button>
        </div>
        <div className="mb-4">
          Total Score: <span className="font-semibold">{total_score}</span>
        </div>
        {renderSection("Parties", parties)}
        {renderSection("Account Information", account_info)}
        {renderSection("Financial Details", financial_details)}
        {renderSection("Payment Structure", payment_structure)}
        {renderSection("Revenue Classification", revenue_classification)}
        {renderSection("Service Level Agreements", sla)}
        <div className="mt-4">
          <h3 className="font-semibold mb-2 text-gray-900">Gap Analysis</h3>
          <ul className="list-disc ml-6 danger">
            {gaps.length === 0 ? (
              <li>No gaps found.</li>
            ) : (
              gaps.map((gap, i) => <li key={i}>{gap}</li>)
            )}
          </ul>
        </div>
      </div>
    </section>
  );
};

export default ContractDetail;
