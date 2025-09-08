"use client";
import React, { useState, useEffect } from "react";
import ContractUpload from "../components/ContractUpload";
import ContractList, { ContractListItem } from "../components/ContractList";

const HomePage = () => {
  const [contracts, setContracts] = useState<ContractListItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  // no inline detail view; details are on their own page (/contracts/[id])

  // Fetch contracts from backend
  const fetchContracts = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/contracts");
      const data = await res.json();
      // Add placeholder fields for name, score, uploaded_at if not present
      setContracts(
        data.map((c: any) => ({
          contract_id: c.contract_id,
          name: c.name || c.contract_id + ".pdf", // fallback
          status: c.status,
          score: c.score ?? 0,
          uploaded_at: c.uploaded_at || new Date().toISOString(),
        }))
      );
    } catch (e) {
      setContracts([]);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchContracts();
  }, []);

  const handleUpload = async (file: File) => {
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      await fetch("http://localhost:8000/contracts/upload", {
        method: "POST",
        body: formData,
      });
      // After upload, refresh contract list
      await fetchContracts();
    } catch (e) {
      // handle error
    }
    setUploading(false);
  };

  // navigation to details is handled by ContractList's link to /contracts/[id]

  return (
    <div className="min-h-screen bg-gray-50">
      <main className="pl-56 pt-8 max-w-4xl mx-auto">
        <ContractUpload onUpload={handleUpload} uploading={uploading} />
        <ContractList contracts={contracts} loading={loading} />
        {/* Contract details open on their own page via the "View" link in the list */}
      </main>
    </div>
  );
};

export default HomePage;
