"use client";
import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import ContractDetail from "../../../components/ContractDetail";

const ContractPage: React.FC = () => {
  const params = useParams();
  const id = params?.id as string;
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const res = await fetch(`http://localhost:8000/contracts/${id}`);
        if (!res.ok) throw new Error("Not ready");
        const json = await res.json();
        setData({
          ...(json.data || {}),
          confidence_scores: json.confidence_scores || {},
          gaps: json.gaps || [],
          score: json.score ?? 0,
        });
      } catch (e) {
        setData(null);
      }
      setLoading(false);
    };
    fetchData();
  }, [id]);

  const router = useRouter();

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      <h1 className="text-2xl font-bold mb-4">Contract {id}</h1>
      <ContractDetail
        data={data}
        loading={loading}
        onClose={() => router.back()}
        contractId={id}
        fullPage
      />
    </div>
  );
};

export default ContractPage;
