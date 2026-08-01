"use client";

import React from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

interface AppShellProps {
  children: React.ReactNode;
  title?: string;
}

export const AppShell: React.FC<AppShellProps> = ({ children, title }) => {
  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden font-sans text-sm">
      <Sidebar />
      <div className="flex-1 flex flex-col h-screen overflow-hidden min-w-0">
        <Header title={title} />
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
};
