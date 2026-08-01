"use client";

import React, { useState } from 'react';
import { useTranslations } from 'next-intl';
import { money, percent } from '@/lib/formatters';
import { Card } from '@/components/ui/Card';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { usePnL } from '@/lib/queries';
import { Loader2 } from 'lucide-react';

export default function PnLScreen() {
  const t = useTranslations('pnl');
  const tl = useTranslations('mockLabels');
  
  const today = new Date();
  const start_date = new Date(today.getFullYear(), today.getMonth(), 1).toISOString();
  const end_date = new Date(today.getFullYear(), today.getMonth() + 1, 0, 23, 59, 59).toISOString();
  
  const { data, isLoading, error } = usePnL({ start_date, end_date });

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-teal-600" />
      </div>
    );
  }

  if (error || !data) {
    return <div className="text-red-500">Failed to load P&L data.</div>;
  }

  // Uses backend margins
  const netProfitStr = data.net_profit || '0';
  const isNetProfitPositive = !netProfitStr.startsWith('-');

  return (
    <div className="space-y-8">
      <SectionTitle>{t('title', { defaultValue: 'P&L Report' })}</SectionTitle>
      
      {/* KPI Tiles */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <Card className="p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider">{t('revenue', { defaultValue: 'Revenue' })}</p>
          <p className="mt-2 text-xl font-bold">{money(data.revenue)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider">{t('grossProfit', { defaultValue: 'Gross Profit' })}</p>
          <p className="mt-2 text-xl font-bold">{money(data.gross_profit)}</p>
          <p className="text-xs text-gray-400 mt-1">{percent(data.gross_margin)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider">{t('ebitda', { defaultValue: 'EBITDA' })}</p>
          <p className="mt-2 text-xl font-bold">{money(data.ebitda)}</p>
          <p className="text-xs text-gray-400 mt-1">{percent(data.ebitda_margin)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider">{t('ebit', { defaultValue: 'EBIT' })}</p>
          <p className="mt-2 text-xl font-bold">{money(data.ebit)}</p>
          <p className="text-xs text-gray-400 mt-1">{percent(data.ebit_margin)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider">{t('ebt', { defaultValue: 'EBT' })}</p>
          <p className="mt-2 text-xl font-bold">{money(data.ebt)}</p>
          <p className="text-xs text-gray-400 mt-1">{percent(data.ebt_margin)}</p>
        </Card>
        <Card className="p-4 border-l-4 border-l-teal-500">
          <p className="text-xs text-gray-500 uppercase tracking-wider">{t('netProfit', { defaultValue: 'Net Profit' })}</p>
          <p className={`mt-2 text-xl font-bold ${isNetProfitPositive ? 'text-green-600' : 'text-red-600'}`}>
            {money(data.net_profit)}
          </p>
          <p className="text-xs text-gray-400 mt-1">{percent(data.net_margin)}</p>
        </Card>
      </div>

      {/* Waterfall P&L */}
      <Card className="p-6 md:p-8 max-w-4xl mx-auto">
        <div className="space-y-4 font-mono text-sm">
          
          <div className="border-t border-slate-300 pt-2 flex justify-between font-bold text-base text-slate-900">
            <span>{t('revenue', { defaultValue: 'Revenue' })}</span>
            <div className="flex justify-end items-center w-48">
              <span className="w-24 text-right">{money(data.revenue)}</span>
              <span className="w-16 text-right text-xs text-slate-500">100%</span>
            </div>
          </div>

          {/* GROSS PROFIT */}
          <div className="flex justify-between text-red-600 ml-4">
            <span>РІв‚¬вЂ™ {tl('Ad spend')}</span>
            <span className="w-24 text-right">({money(data.ad_spend)})</span>
          </div>

          <div className="border-t-2 border-slate-300 pt-2 flex justify-between font-bold text-base text-slate-900">
            <span>= {t('grossProfit', { defaultValue: 'Gross Profit' })}</span>
            <div className="flex justify-end items-center w-48">
              <span className="w-24 text-right">{money(data.gross_profit)}</span>
              <span className="w-16 text-right text-xs text-slate-500">{percent(data.gross_margin)}</span>
            </div>
          </div>

          {/* OPEX */}
          <div className="flex justify-between text-red-600 pt-2 ml-4">
            <span>РІв‚¬вЂ™ {tl('Consumables')}</span>
            <span className="w-24 text-right">({money(data.consumables)})</span>
          </div>
          <div className="flex justify-between text-red-600 ml-4">
            <span>РІв‚¬вЂ™ {tl('Other OPEX')}</span>
            <span className="w-24 text-right">({money(data.operating_expenses)})</span>
          </div>

          {/* EBITDA */}
          <div className="border-t-2 border-slate-300 pt-2 flex justify-between font-bold text-base text-slate-900">
            <span>= {t('ebitda', { defaultValue: 'EBITDA' })}</span>
            <div className="flex justify-end items-center w-48">
              <span className="w-24 text-right">{money(data.ebitda)}</span>
              <span className="w-16 text-right text-xs text-slate-500">{percent(data.ebitda_margin)}</span>
            </div>
          </div>

          {/* EBIT */}
          <div className="flex justify-between text-red-600 pt-2 ml-4">
            <span>РІв‚¬вЂ™ {tl('Depreciation & Amortization')}</span>
            <span className="w-24 text-right">({money(data.depreciation)})</span>
          </div>

          <div className="border-t-2 border-slate-300 pt-2 flex justify-between font-bold text-base text-slate-900">
            <span>= {t('ebit', { defaultValue: 'EBIT' })}</span>
            <div className="flex justify-end items-center w-48">
              <span className="w-24 text-right">{money(data.ebit)}</span>
              <span className="w-16 text-right text-xs text-slate-500">{percent(data.ebit_margin)}</span>
            </div>
          </div>

          {/* EBT */}
          <div className="flex justify-between text-red-600 pt-2 ml-4">
            <span>РІв‚¬вЂ™ {tl('Interest Expense')}</span>
            <span className="w-24 text-right">({money(data.interest)})</span>
          </div>

          <div className="border-t-2 border-slate-300 pt-2 flex justify-between font-bold text-base text-slate-900">
            <span>= {t('ebt', { defaultValue: 'EBT' })}</span>
            <div className="flex justify-end items-center w-48">
              <span className="w-24 text-right">{money(data.ebt)}</span>
              <span className="w-16 text-right text-xs text-slate-500">{percent(data.ebt_margin)}</span>
            </div>
          </div>

          {/* NET PROFIT */}
          <div className="flex justify-between text-red-600 pt-2 ml-4">
            <span>РІв‚¬вЂ™ {tl('Income Tax')}</span>
            <span className="w-24 text-right">({money(data.tax)})</span>
          </div>

          <div className="border-t-[3px] border-slate-800 pt-2 flex justify-between font-bold text-lg text-slate-900">
            <span>= {t('netProfit', { defaultValue: 'Net Profit' })}</span>
            <div className="flex justify-end items-center w-48">
              <span className={`w-24 text-right ${isNetProfitPositive ? 'text-green-600' : 'text-red-600'}`}>{money(data.net_profit)}</span>
              <span className="w-16 text-right text-xs text-slate-500 font-normal">{percent(data.net_margin)}</span>
            </div>
          </div>

        </div>
      </Card>
      
      {/* Explanations */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm text-slate-600 mt-8 max-w-4xl mx-auto">
        <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
          <strong className="block text-slate-800 mb-1">{t('grossProfit', { defaultValue: 'Gross Profit' })}</strong>
          {t('grossProfitExplanation', { defaultValue: 'Shows the profitability of traffic before accounting for operational costs.' })}
        </div>
        <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
          <strong className="block text-slate-800 mb-1">{t('ebitda', { defaultValue: 'EBITDA' })}</strong>
          {t('ebitdaExplanation', { defaultValue: 'Operating profit before D&A, interest, and taxes.' })}
        </div>
        <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
          <strong className="block text-slate-800 mb-1">{t('depreciation', { defaultValue: 'D&A' })} & {t('interestExpense', { defaultValue: 'Interest' })}</strong>
          {t('daInterestExplanation', { defaultValue: 'Interest can be significant when crediting ad spend (Net-30 cash gap).' })}
        </div>
      </div>
    </div>
  );
}




