"use client";

import React, { useState } from 'react';
import { useTranslations } from 'next-intl';
import { money, percent } from '@/lib/formatters';
import { Card } from '@/components/ui/Card';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { ChevronDown, ChevronUp, Filter, Loader2 } from 'lucide-react';
import { useCampaignRuns } from '@/lib/queries';

export default function CampaignsScreen() {
  const t = useTranslations('campaigns');
  const tCommon = useTranslations('common');
  const [verticalFilter, setVerticalFilter] = useState('');
  const [sortKey, setSortKey] = useState('revenue');
  const [sortDir, setSortDir] = useState<'asc'|'desc'>('desc');
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const { data, isLoading, error } = useCampaignRuns({ skip: 0, limit: 100 });

  if (isLoading) {
    return <div className="flex h-64 items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-teal-600" /></div>;
  }

  if (error || !data) {
    return <div className="text-red-500">{t('loadError')}</div>;
  }

  const items = data || [];
  
  // Quick hack to filter out duplicates or missing verticals
  const verticals = Array.from(new Set(items.map((c: any) => c.vertical || t('unknown')))).filter(Boolean);

  let filtered = items;
  if (verticalFilter) {
    filtered = filtered.filter((c: any) => (c.vertical || t('unknown')) === verticalFilter);
  }

  filtered.sort((a: any, b: any) => {
    // Basic sorting string comparison or numeric
    const valA = a[sortKey] || 0;
    const valB = b[sortKey] || 0;
    
    if (valA < valB) return sortDir === 'asc' ? -1 : 1;
    if (valA > valB) return sortDir === 'asc' ? 1 : -1;
    return 0;
  });

  const toggleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const renderSortIcon = (colKey: string) => {
    if (sortKey !== colKey) return <span className="w-4 inline-block" />;
    return sortDir === 'asc' ? <ChevronUp size={14} className="inline" /> : <ChevronDown size={14} className="inline" />;
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <SectionTitle>{t('title')}</SectionTitle>
        <div className="flex items-center gap-2">
          <Filter size={16} className="text-gray-500" />
          <select 
            className="border-gray-300 rounded-md text-sm pl-3 pr-8 py-2 focus:ring-teal-500 focus:border-teal-500"
            value={verticalFilter}
            onChange={e => setVerticalFilter(e.target.value)}
          >
            <option value="">{t('filterAll')}</option>
            {verticals.map(v => <option key={String(v)} value={String(v)}>{String(v)}</option>)}
          </select>
        </div>
      </div>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-gray-900 cursor-pointer" onClick={() => toggleSort('name')}>
                  {t('colCampaign')} {renderSortIcon('name')}
                </th>
                <th className="px-4 py-3 text-left font-semibold text-gray-900 cursor-pointer" onClick={() => toggleSort('platform')}>
                  {t('colPlatform')} {renderSortIcon('platform')}
                </th>
                <th className="px-4 py-3 text-right font-semibold text-gray-900 cursor-pointer" onClick={() => toggleSort('spend')}>
                  {t('colSpend')} {renderSortIcon('spend')}
                </th>
                <th className="px-4 py-3 text-right font-semibold text-gray-900 cursor-pointer" onClick={() => toggleSort('revenue')}>
                  {t('colRevenue')} {renderSortIcon('revenue')}
                </th>
                <th className="px-4 py-3 text-right font-semibold text-gray-900 cursor-pointer" onClick={() => toggleSort('roi')}>
                  {t('colROI')} {renderSortIcon('roi')}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filtered.map((c: any) => (
                <React.Fragment key={c.id}>
                  <tr 
                    className="hover:bg-gray-50 cursor-pointer transition-colors"
                    onClick={() => setExpandedRow(expandedRow === c.id ? null : c.id)}
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900">{c.name}</div>
                      <div className="text-xs text-gray-500">{c.vertical || t('unknown')}</div>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{c.platform || t('unknown')}</td>
                    <td className="px-4 py-3 text-right text-gray-900">{money(c.spend)}</td>
                    <td className="px-4 py-3 text-right text-gray-900">{money(c.revenue)}</td>
                    <td className="px-4 py-3 text-right font-medium">
                      <span className={c.roi && !c.roi.toString().startsWith('-') ? 'text-green-600' : 'text-red-600'}>
                        {percent(c.roi)}
                      </span>
                    </td>
                  </tr>
                  {expandedRow === c.id && (
                    <tr className="bg-gray-50 border-b border-gray-200 shadow-inner">
                      <td colSpan={5} className="px-4 py-4">
                        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center text-xs">
                          <div className="bg-white p-2 rounded shadow-sm">
                            <div className="text-gray-500 mb-1">{tCommon('roas')}</div>
                            <div className="font-bold">{c.roas || '-'}</div>
                          </div>
                          <div className="bg-white p-2 rounded shadow-sm">
                            <div className="text-gray-500 mb-1">{t('cpa')}</div>
                            <div className="font-bold">{c.cpa ? money(c.cpa) : '-'}</div>
                          </div>
                          <div className="bg-white p-2 rounded shadow-sm">
                            <div className="text-gray-500 mb-1">{t('ctr')}</div>
                            <div className="font-bold">{c.ctr ? percent(c.ctr) : '-'}</div>
                          </div>
                          <div className="bg-white p-2 rounded shadow-sm">
                            <div className="text-gray-500 mb-1">{t('conversions')}</div>
                            <div className="font-bold">{c.conversions || '-'}</div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                    {t('noCampaigns')}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}





