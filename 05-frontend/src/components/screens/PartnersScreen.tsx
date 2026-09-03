"use client";

import React, { useState } from 'react';
import { usePartners } from '@/lib/queries';
import { useTranslations } from 'next-intl';
import { money } from '@/lib/formatters';
import { Card } from '@/components/ui/Card';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { PAYOUT_STATUSES } from '@/lib/constants';
import { ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';

export default function PartnersScreen() {
  const { data, isLoading, error } = usePartners();
  const t = useTranslations('partners');
  const tc = useTranslations('common');

  const [networkFilter, setNetworkFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  
  const [sortKey, setSortKey] = useState<string>('booked_on');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  if (isLoading) {
    return <div className="flex h-64 items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-teal-600" /></div>;
  }

  if (error || !data) {
    return <div className="text-red-500">{t('loadError')}</div>;
  }

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const filteredPayouts = (data.payouts || [])
    .filter((p: any) => !networkFilter || p.network_id === networkFilter)
    .filter((p: any) => !statusFilter || p.status === statusFilter)
    .sort((a: any, b: any) => {
      const valA = a[sortKey];
      const valB = b[sortKey];
      if (valA === undefined || valB === undefined || valA === null || valB === null) return 0;
      if (valA < valB) return sortDir === 'asc' ? -1 : 1;
      if (valA > valB) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });

  const renderSortIcon = (col: string) => {
    if (sortKey !== col) return null;
    return sortDir === 'asc' ? <ChevronUp size={12} /> : <ChevronDown size={12} />;
  };

  return (
    <div className="space-y-6">
      <SectionTitle>{t('title')}</SectionTitle>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="p-4">
          <p className="text-sm text-gray-500">{t('kpiBooked')}</p>
          <p className="mt-2 text-2xl font-bold">{money(data.kpi_total_booked)}</p>
        </Card>
        <Card className="p-4 border-l-4 border-l-amber-500">
          <p className="text-sm text-gray-500">{t('kpiInHold')}</p>
          <p className="mt-2 text-2xl font-bold text-amber-600">{money(data.kpi_in_hold)}</p>
        </Card>
        <Card className="p-4 border-l-4 border-l-green-500">
          <p className="text-sm text-gray-500">{t('kpiNetConfirmed')}</p>
          <p className="mt-2 text-2xl font-bold text-green-600">{money(data.kpi_net_confirmed)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-gray-500">{t('kpiScrubRate')}</p>
          <p className="mt-2 text-2xl font-bold text-gray-900">
            {data.kpi_avg_scrub ? 
              (() => {
                const parts = data.kpi_avg_scrub.split('.');
                const int = parts[0] || '0';
                const frac = (parts[1] || '0000').padEnd(4, '0');
                const val = BigInt(int + frac);
                // val is now scaled by 10000 (4 decimals). e.g., 0.1250 -> 1250
                // To get percentage with 1 decimal (e.g. 12.5), we need (val / 1000n).toString() and then add decimal point.
                const scaled = val / BigInt(10); // scaled by 1000. 1250 / 10 = 125. Which is 12.5%.
                const str = scaled.toString();
                return (str.slice(0, -1) || '0') + '.' + str.slice(-1) + '%';
              })()
              : '0.0%'}
          </p>
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
                {(data.networks || []).map((n: any) => (
                  <tr key={n.id} className="border-b border-gray-50 last:border-0 hover:bg-gray-50">
                    <td className="py-3 px-2 font-medium">{n.name}</td>
                    <td className="py-3 px-2 text-right">{money("0")}</td>
                    <td className="py-3 px-2 text-right">{money("0")}</td>
                    <td className="py-3 px-2 text-right">0%</td>
                    <td className="py-3 px-2 text-right">{money("0")}</td>
                  </tr>
                ))}
                {(!data.networks || data.networks.length === 0) && (
                  <tr><td colSpan={5} className="py-8 text-center text-gray-500">{t('noNetworks')}</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
        
        <Card className="p-6 lg:col-span-1">
          <h3 className="mb-4 text-lg font-semibold">{t('expectedArrivals')}</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.expected_cash || []}>
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
                {(data.networks || []).map((n: any) => (
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
              {filteredPayouts.map((p: any) => (
                <tr key={p.id} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="py-3 px-2">{p.network_id}</td>
                  <td className="py-3 px-2">{p.campaign_run_id}</td>
                  <td className="py-3 px-2">{p.status}</td>
                  <td className="py-3 px-2 text-right">{money(p.amount)}</td>
                  <td className="py-3 px-2">{p.booked_on}</td>
                  <td className="py-3 px-2">{p.hold_until || '-'}</td>
                </tr>
              ))}
              {filteredPayouts.length === 0 && (
                <tr><td colSpan={6} className="py-8 text-center text-gray-500">{t('noPayouts')}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}












