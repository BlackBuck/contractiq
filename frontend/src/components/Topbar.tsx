import React from "react";

const Topbar: React.FC = () => (
  <header className="w-full bg-white shadow px-6 py-4 flex flex-row-reverse items-end-safe z-50">
    <div>
      <span className="text-gray-500">Welcome, User</span>
    </div>
  </header>
);

export default Topbar;
