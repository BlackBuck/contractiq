import React from "react";
import Link from "next/link";

export interface ContractListItem {
  contract_id: string;
  name: string;
  status: string;
  score: number;
  uploaded_at: string;
}

interface ContractListProps {
  contracts: ContractListItem[];
  onSelect?: (id: string) => void;
  loading: boolean;
}

const statusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  processing: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

const ContractList: React.FC<ContractListProps> = ({
  contracts,
  loading,
  onSelect,
}) => {
  return (
    <div className="overflow-x-auto mt-6 rounded-lg border border-gray-200 p-1">
      <table className="min-w-full bg-white border border-gray-200 rounded-2xl overflow-hidden">
        <thead>
          <tr>
            <th className="px-4 py-2 text-left text-gray-900 font-bold bg-white">
              Name
            </th>
            <th className="px-4 py-2 text-left text-gray-900 font-bold bg-white">
              Status
            </th>
            <th className="px-4 py-2 text-left text-gray-900 font-bold bg-white">
              Score
            </th>
            <th className="px-4 py-2 text-left text-gray-900 font-bold bg-white">
              Uploaded
            </th>
            <th className="px-4 py-2 text-left text-gray-900 font-bold bg-white">
              Action
            </th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan={5} className="text-center py-8 text-gray-700">
                Loading...
              </td>
            </tr>
          ) : contracts.length === 0 ? (
            <tr>
              <td colSpan={5} className="text-center py-8 text-gray-700">
                No contracts found.
              </td>
            </tr>
          ) : (
            contracts.map((contract) => (
              <tr
                key={contract.contract_id}
                className="border-t border-gray-200 hover:bg-gray-50 transition-colors">
                <td className="px-4 py-2 text-gray-900 font-medium">
                  {contract.name}
                </td>
                <td className="px-4 py-2">
                  <span
                    className={`px-2 py-1 rounded text-xs font-semibold ${
                      statusColors[contract.status] ||
                      "bg-gray-100 text-gray-800"
                    }`}>
                    {contract.status}
                  </span>
                </td>
                <td
                  className={`px-4 py-2 font-semibold ${
                    contract.score > 80
                      ? "text-green-700"
                      : contract.score >= 50
                      ? "text-yellow-700"
                      : "text-red-700"
                  }`}>
                  {contract.score ?? "-"}
                </td>
                <td className="px-4 py-2 text-gray-900">
                  {new Date(contract.uploaded_at).toLocaleString()}
                </td>
                <td className="px-4 py-2">
                  <Link
                    className="text-blue-600 hover:underline"
                    href={`/contracts/${contract.contract_id}`}
                    onClick={() => onSelect && onSelect(contract.contract_id)}>
                    View
                  </Link>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};

export default ContractList;
