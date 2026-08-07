"use client";

import { useTranslations } from 'next-intl';
import { money } from '@/lib/formatters';
import { Card } from '@/components/ui/Card';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Info, Loader2 } from 'lucide-react';
import { useCashFlow } from '@/lib/queries';

export default function CashFlowScreen() {
  const t = useTranslations('cashflow');

  const today = new Date();
  const start_date = new Date(today.getFullYear(), today.getMonth(), 1).toISOString();
  const end_date = new Date(today.getFullYear(), today.getMonth() + 1, 0, 23, 59, 59).toISOString();

  const { data, isLoading, error } = useCashFlow({ start_date, end_date });
  const tc = useTranslations('common');

  if (isLoading) {
    return <div className="flex h-64 items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-teal-600" /></div>;
  }

  if (error || !data) {
    return <div className="text-red-500">{tc('noData')}</div>;
  }

  // Use the actual fields from CashFlowResult
  const runway = data.runway_days ? String(data.runway_days) + ' ' + tc('days') : tc('na');
  const opening = money(data.transaction_balance);
  const receipts = money("0");
  const outflows = money("0");
  const closing = money(data.available_balance);

  return (
    <div className="space-y-6">
      <SectionTitle>{t('title')}</SectionTitle>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="p-6 md:col-span-1 bg-teal-50 border-teal-100 flex flex-col justify-center items-center text-center">
          <div className="text-teal-900 text-sm font-medium mb-2 flex items-center gap-1">
            {t('cashRunway')} <Info size={14} className="text-teal-600"/>
          </div>
          <div className="text-4xl font-bold text-teal-700">{runway}</div>
          <div className="text-xs text-teal-600 mt-2">{t('runwayExplanation')}</div>
        </Card>

        <Card className="p-6 md:col-span-2">
          <div className="text-sm font-medium text-gray-500 mb-4 uppercase tracking-wider">{t('balanceMovement')}</div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <div className="text-xs text-gray-500 mb-1">{t('opening')}</div>
              <div className="text-xl font-bold text-gray-900">{opening}</div>
            </div>
            <div>
              <div className="text-xs text-gray-500 mb-1">{t('receipts')}</div>
              <div className="text-xl font-bold text-green-600">+{receipts}</div>
            </div>
            <div>
              <div className="text-xs text-gray-500 mb-1">{t('outflow')}</div>
              <div className="text-xl font-bold text-red-600">-{outflows}</div>
            </div>
            <div>
              <div className="text-xs text-gray-500 mb-1">{t('closing')}</div>
              <div className="text-xl font-bold text-gray-900">{closing}</div>
            </div>
          </div>
        </Card>
      </div>

      <Card className="p-6 h-[400px] flex flex-col">
        <div className="text-sm font-medium text-gray-500 mb-6 uppercase tracking-wider">{t('cashFlowTrend')}</div>
        <div className="flex-1 min-h-0 text-gray-400 flex items-center justify-center">
          {tc('chartNeedsData')}
        </div>
      </Card>
    </div>
  );
}


