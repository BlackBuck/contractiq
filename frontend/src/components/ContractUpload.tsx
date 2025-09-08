import React, { useRef } from "react";

interface ContractUploadProps {
  onUpload: (file: File) => void;
  uploading: boolean;
}

const ContractUpload: React.FC<ContractUploadProps> = ({
  onUpload,
  uploading,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onUpload(e.target.files[0]);
    }
  };

  return (
    <div
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
      className="border-2 border-gray-200 border-dashed rounded-lg p-8 text-center cursor-pointer bg-white hover:bg-gray-50 shadow-md transition-colors"
      onClick={() => fileInputRef.current?.click()}
      style={{ minHeight: 120 }}>
      <input
        type="file"
        accept="application/pdf"
        ref={fileInputRef}
        style={{ display: "none" }}
        onChange={handleFileChange}
        disabled={uploading}
      />
      {uploading ? (
        <span className="text-gray-700 font-semibold">Uploading...</span>
      ) : (
        <span className="text-gray-900 font-semibold">
          Drag & drop a PDF contract here, or click to select
        </span>
      )}
    </div>
  );
};

export default ContractUpload;
