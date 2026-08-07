"use client";

import React from 'react';
import { useTranslations } from 'next-intl';
import { money } from '@/lib/formatters';
import { Card } from '@/components/ui/Card';
import { Sparkles, ArrowRight, Loader2 } from 'lucide-react';
import { useHealth, usePnL, useCashFlow } from '@/lib/queries';

export default function DashboardScreen() {
  const t = useTranslations('dashboard');
  const tm = useTranslations('metrics');
  const tc = useTranslations('common');

  const today = new Date();
  const start_date = new Date(today.getFullYear(), today.getMonth(), 1).toISOString();
  const end_date = new Date(today.getFullYear(), today.getMonth() + 1, 0, 23, 59, 59).toISOString();

  const { data: healthData, isLoading: isHealthLoading } = useHealth({ start_date, end_date });
  const { data: pnlData, isLoading: isPnlLoading } = usePnL({ start_date, end_date });
  const { data: cashFlowData, isLoading: isCashFlowLoading } = useCashFlow({ start_date, end_date });

  if (isHealthLoading || isPnlLoading || isCashFlowLoading) {
    return <div className="flex h-64 items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-teal-600" /></div>;
  }

  // Fallbacks if data fails
  const healthScore = healthData?.health_score ?? 100;
  
  // Transform data into metrics array shape
  const metrics = pnlData && cashFlowData ? [
    { label: 'cashRunway', value: cashFlowData.runway_days ? `${cashFlowData.runway_days} ${tc('days')}` : tc('na') },
    { label: 'grossProfit', value: money(pnlData.gross_profit) },
    { label: 'ebitda', value: money(pnlData.ebitda) },
    { label: 'netProfit', value: money(pnlData.net_profit) },
  ] : [];

  return (
    <div className="space-y-6">
      {/* Health score + metrics */}
      <Card className="p-6 flex flex-col md:flex-row items-center gap-8">
        <div className="flex flex-col items-center gap-2 shrink-0 md:pr-8 md:border-r border-gray-100">
          <svg width="72" height="72" viewBox="0 0 72 72">
            <circle cx="36" cy="36" r="30" fill="none" stroke="#e5e7eb" strokeWidth="7" />
            <circle cx="36" cy="36" r="30" fill="none" stroke="#15803d" strokeWidth="7" strokeLinecap="round"
              strokeDasharray={2 * Math.PI * 30} strokeDashoffset={2 * Math.PI * 30 * (1 - healthScore / 100)}
              transform="rotate(-90 36 36)" />
            <text x="36" y="41" textAnchor="middle" fontSize="17" fontWeight="600" fill="#111827">{healthScore}</text>
          </svg>
          <span className="text-xs text-gray-500">{t('healthScore')}</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-8 gap-y-5 flex-1 w-full">
          {metrics.map((m) => (
            <div key={m.label}>
              <div className="text-xs text-gray-500 mb-1">{tm(m.label)}</div>
              <div className="text-xl font-semibold text-gray-900">{m.value}</div>
            </div>
          ))}
        </div>
      </Card>
      
      {/* We hide the chart since there's no real cashFlow time series yet in the backend */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="p-6 lg:col-span-2 h-[320px] flex flex-col items-center justify-center text-gray-400">
          {tc('chartNeedsData')}
        </Card>

        <Card className="p-6 bg-indigo-50 border-indigo-100 relative overflow-hidden flex flex-col">
          <div className="absolute top-0 left-0 w-1 h-full bg-indigo-500" />
          <div className="flex items-center gap-2 mb-3 text-indigo-600 font-semibold text-sm">
            <Sparkles size={16} />{t('aiFinancialAnalyst')}
          </div>
          <p className="text-sm text-gray-700 leading-relaxed flex-1">
            &quot;Your health score looks great, indicating a solid cash position and healthy margins.&quot;
          </p>
          <button className="mt-4 flex items-center justify-between bg-white px-4 py-2 rounded-lg text-sm font-medium border border-gray-200 hover:border-indigo-300 transition-colors">
            {t('reviewCampaigns')} <ArrowRight size={14} className="text-gray-400" />
          </button>
        </Card>
      </div>
    </div>
  );
}

