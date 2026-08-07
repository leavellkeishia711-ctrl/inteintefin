"use client";

import Image from 'next/image';
import React from 'react';
import { Link, usePathname } from '@/i18n/routing';

import {
  LayoutDashboard, LineChart, Wallet, Megaphone, BrainCircuit, Settings, Banknote, BookOpen, Handshake, Receipt
} from 'lucide-react';

const NAV_ITEMS = [
  { id: '/', icon: LayoutDashboard, labelKey: 'Dashboard' },
  { id: '/transactions', icon: Receipt, labelKey: 'Transactions' },
  { id: '/pnl', icon: LineChart, labelKey: 'P&L' },
  { id: '/cashflow', icon: Wallet, labelKey: 'Cash Flow' },
  { id: '/campaigns', icon: Megaphone, labelKey: 'Campaigns' },
  { id: '/partners', icon: Handshake, labelKey: 'Partners' },
  { id: '/payroll', icon: Banknote, labelKey: 'Payroll' },
  { id: '/ai-analyst', icon: BrainCircuit, labelKey: 'AI Analyst' },
  { id: '/guides', icon: BookOpen, labelKey: 'Guides' },
];

export const Sidebar = () => {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/';
    return pathname.startsWith(href);
  };

  return (
    <aside className="hidden md:flex w-64 border-r border-gray-200 h-screen flex-col bg-white shrink-0 transition-all">
      <div className="p-6">
        <h1 className="text-xl font-bold tracking-tight text-gray-900 flex items-center gap-2">
          <Image src="/logo-icon-v2.png" alt="FinanceIntel Logo" width={24} height={24} className="rounded-md" />
          FinanceIntel
        </h1>
      </div>

      <nav className="flex-1 px-4 space-y-1">
        {NAV_ITEMS.map((item) => {
          const active = isActive(item.id);
          return (
            <Link
              key={item.id}
              href={item.id}
              className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                active
                  ? 'bg-teal-50 text-teal-700'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              <item.icon size={18} className={active ? 'text-teal-600' : 'text-gray-400'} />
              {item.labelKey}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 mt-auto">
        <Link
          href="/settings"
          className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
            isActive('/settings')
              ? 'bg-teal-50 text-teal-700'
              : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
          }`}
        >
          <Settings size={18} className={isActive('/settings') ? 'text-teal-600' : 'text-gray-400'} />
          Settings
        </Link>
      </div>
    </aside>
  );
};

