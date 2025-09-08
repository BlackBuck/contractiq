"use client";
import React, { useState } from "react";
import { LayoutDashboard, FileText, Settings } from "lucide-react";

const menu = [
  {
    label: "Dashboard",
    icon: <LayoutDashboard className="w-6 h-6" />,
  },
  {
    label: "Contracts",
    icon: <FileText className="w-6 h-6" />,
  },
  {
    label: "Settings",
    icon: <Settings className="w-6 h-6" />,
  },
];

const Sidebar: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  return (
    <aside
      className={`h-screen bg-white shadow flex flex-col py-8 px-2 fixed top-0 left-0 z-10 transition-all duration-200 ${
        collapsed ? "w-20" : "w-56"
      }`}>
      <div className="flex items-center justify-between mb-8 px-2">
        {!collapsed && (
          <span className="text-2xl font-extrabold text-blue-700 tracking-tight">
            ContractIQ
          </span>
        )}
        <button
          className="ml-auto p-1 rounded hover:bg-gray-100 text-gray-500"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          onClick={() => setCollapsed((c) => !c)}>
          {!collapsed ? (
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15 19l-7-7 7-7"
              />
            </svg>
          ) : (
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 5l7 7-7 7"
              />
            </svg>
          )}
        </button>
      </div>
      <nav>
        <ul
          className={`flex flex-col gap-4 mt-2 ${
            collapsed ? "items-center" : ""
          }`}>
          {menu.map((item) => (
            <li key={item.label}>
              <button
                className={`flex items-center gap-3 w-full px-2 py-2 rounded text-gray-700 hover:text-blue-600 hover:bg-gray-50 transition ${
                  collapsed ? "justify-center" : ""
                }`}>
                {item.icon}
                {!collapsed && (
                  <span className="font-medium">{item.label}</span>
                )}
              </button>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
};

export default Sidebar;
