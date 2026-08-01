"use client";

import React, { useState } from 'react';
import { usePartners } from '@/lib/queries';
import { useTranslations } from 'next-intl';
import { networksData, payoutsData, partnersSummary } from '@/lib/partnersData';
import { money } from '@/lib/formatters';
import { Card } from '@/components/ui/Card';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { payoutStatusLabel, networkLabel, PAYOUT_STATUSES } from '@/lib/constants';
import { AlertCircle, CheckCircle2, Clock, Ban, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';
import type { PayoutRecord, AffiliateNetworkInfo } from '@/lib/partnersData';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';

type SortKey = keyof PayoutRecord;

const getToneColor = (status: string) => {
  const tone = PAYOUT_STATUSES.find(s => s.value === status)?.tone;
  switch (tone) {
    case 'ok': return 'text-green-600 bg-green-50 border-green-200';
    case 'warning': return 'text-amber-600 bg-amber-50 border-amber-200';
    case 'danger': return 'text-red-600 bg-red-50 border-red-200';
    case 'neutral': return 'text-gray-600 bg-gray-50 border-gray-200';
    default: return 'text-gray-600 bg-gray-50 border-gray-200';
  }
};

const getToneIcon = (status: string) => {
  const tone = PAYOUT_STATUSES.find(s => s.value === status)?.tone;
  switch (tone) {
    case 'ok': return <CheckCircle2 size={14} />;
    case 'warning': return <Clock size={14} />;
    case 'danger': return <AlertTriangle size={14} />;
    case 'neutral': return <Ban size={14} />;
    default: return null;
  }
};

export default function PartnersScreen() {
  const { data, isLoading } = usePartners();
  const t = useTranslations('partners');
  const tc = useTranslations('common');
  const tl = useTranslations('mockLabels');

  const [networkFilter, setNetworkFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  
  const [sortKey, setSortKey] = useState<SortKey | ''>('bookedOn');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const filteredPayouts = payoutsData
    .filter(p => !networkFilter || p.networkId === networkFilter)
    .filter(p => !statusFilter || p.status === statusFilter)
    .sort((a, b) => {
      if (!sortKey) return 0;
      const valA = a[sortKey];
      const valB = b[sortKey];
      if (valA === undefined || valB === undefined || valA === null || valB === null) return 0;
      if (valA < valB) return sortDir === 'asc' ? -1 : 1;
      if (valA > valB) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });

  const renderSortIcon = (col: SortKey) => {
    if (sortKey !== col) return null;
    return sortDir === 'asc' ? <ChevronUp size={12} /> : <ChevronDown size={12} />;
  };

  // Mock data for chart: aggregate pending payouts by week of holdUntil
  const expectedCashData: any[] = [];

  return (
    <div className="space-y-6">
      <SectionTitle>{t('title')}</SectionTitle>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="p-4">
          <p className="text-sm text-gray-500">{t('kpiBooked')}</p>
          <p className="mt-2 text-2xl font-bold">{money(String(partnersSummary.totalBooked))}</p>
        </Card>
        <Card className="p-4 border-l-4 border-l-amber-500">
          <p className="text-sm text-gray-500">{t('kpiInHold')}</p>
          <p className="mt-2 text-2xl font-bold text-amber-600">{money(String(partnersSummary.totalInHold))}</p>
        </Card>
        <Card className="p-4 border-l-4 border-l-green-500">
          <p className="text-sm text-gray-500">{t('kpiNetConfirmed')}</p>
          <p className="mt-2 text-2xl font-bold text-green-600">{money(String(partnersSummary.totalNetConfirmed))}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-gray-500">{t('kpiScrubRate')}</p>
          <p className="mt-2 text-2xl font-bold text-gray-900">{partnersSummary.blendedScrubRate.toFixed(1)}%</p>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="p-6 lg:col-span-2">
          <h3 className="mb-4 text-lg font-semibold">{t('network')}</h3>
          <div className="overflow-x-auto -mx-2">
            <table className="w-full text-sm min-w-[600px]">
              <thead>
                <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                  <th className="font-medium py-2 px-2">{t('network')}</th>
                  <th className="font-medium py-2 px-2 text-right">{t('kpiBooked')}</th>
                  <th className="font-medium py-2 px-2 text-right">{t('kpiInHold')}</th>
                  <th className="font-medium py-2 px-2 text-right">{t('kpiScrubRate')}</th>
                  <th className="font-medium py-2 px-2 text-right">{t('kpiNetConfirmed')}</th>
                </tr>
              </thead>
              <tbody>
                <tr><td colSpan={6} className="py-8 text-center text-gray-500">No payouts found.</td></tr>
              </tbody>
            </table>
          </div>
        </Card>
        
        <Card className="p-6 lg:col-span-1">
          <h3 className="mb-4 text-lg font-semibold">{t('expectedArrivals')}</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data?.expected_cash || []}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#888' }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#888' }} tickFormatter={(val) => `$${val/1000}k`} />
                <Tooltip 
                  formatter={(value: any) => [money(String(value ?? 0)), t('kpiInHold')]}
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                />
                <Bar dataKey="amount" fill="#14b8a6" radius={[4, 4, 0, 0]} maxBarSize={40} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <Card className="p-6">
        <SectionTitle
          action={
            <div className="flex gap-2">
              <select
                value={networkFilter}
                onChange={(e) => setNetworkFilter(e.target.value)}
                className="flex items-center gap-1 text-sm text-gray-500 border border-gray-200 rounded-md px-2.5 py-1 bg-white"
              >
                <option value="">{t('network')} ({tc('total')})</option>
                {(data?.networks || []).map((n: any) => (
                  <option key={n.id} value={n.id}>{n.name}</option>
                ))}
              </select>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="flex items-center gap-1 text-sm text-gray-500 border border-gray-200 rounded-md px-2.5 py-1 bg-white"
              >
                <option value="">{t('status')} ({tc('total')})</option>
                {PAYOUT_STATUSES.map(s => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
          }
        >
          {t('details')}
        </SectionTitle>

        <div className="overflow-x-auto -mx-2 mt-4">
          <table className="w-full text-sm min-w-[900px]">
            <thead>
              <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                <th className="font-medium py-2 px-2 cursor-pointer" onClick={() => handleSort('networkName')}>
                  <span className="flex items-center gap-1">{t('network')} {renderSortIcon('networkName')}</span>
                </th>
                <th className="font-medium py-2 px-2 cursor-pointer" onClick={() => handleSort('campaignName')}>
                  <span className="flex items-center gap-1">{t('campaign')} {renderSortIcon('campaignName')}</span>
                </th>
                <th className="font-medium py-2 px-2 cursor-pointer" onClick={() => handleSort('status')}>
                  <span className="flex items-center gap-1">{t('status')} {renderSortIcon('status')}</span>
                </th>
                <th className="font-medium py-2 px-2 cursor-pointer text-right" onClick={() => handleSort('amount')}>
                  <span className="flex items-center justify-end gap-1">{t('amount')} {renderSortIcon('amount')}</span>
                </th>
                <th className="font-medium py-2 px-2 cursor-pointer" onClick={() => handleSort('bookedOn')}>
                  <span className="flex items-center gap-1">{t('bookedOn')} {renderSortIcon('bookedOn')}</span>
                </th>
                <th className="font-medium py-2 px-2 cursor-pointer" onClick={() => handleSort('holdUntil')}>
                  <span className="flex items-center gap-1">{t('holdUntil')} {renderSortIcon('holdUntil')}</span>
                </th>
              </tr>
            </thead>
            <tbody>
                <tr><td colSpan={6} className="py-8 text-center text-gray-500">No payouts found.</td></tr>
              </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}












