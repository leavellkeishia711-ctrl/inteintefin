"use client";

import React from 'react';
import { useTranslations } from 'next-intl';
import { money } from '@/lib/formatters';
import { Card } from '@/components/ui/Card';
import { SectionTitle } from '@/components/ui/SectionTitle';

import { usePayroll } from '@/lib/queries';
export default function PayrollScreen() {
  const { data, isLoading, error } = usePayroll();
  const t = useTranslations('payroll');
  const tc = useTranslations('common');
  
  if (isLoading) {
    return <div className="p-8 text-center text-gray-500">{tc('loading')}</div>;
  }
  
  if (error) {
    return <div className="p-8 text-center text-red-500">{tc('noData')}</div>;
  }

  return (
    <div className="space-y-6">
      <SectionTitle>{t('title')}</SectionTitle>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="p-4 bg-gray-50 text-center">
          <div className="text-sm text-gray-500 mb-1">{t('totalPayroll')}</div>
          <div className="text-2xl font-bold">{money(data?.total_payroll || '0')}</div>
        </Card>
        <Card className="p-4 bg-gray-50 text-center">
          <div className="text-sm text-gray-500 mb-1">{t('activeEmployees')}</div>
          <div className="text-2xl font-bold">{data?.active_employees || 0}</div>
        </Card>
        <Card className="p-4 bg-gray-50 text-center">
          <div className="text-sm text-gray-500 mb-1">{t('pendingApproval')}</div>
          <div className="text-2xl font-bold">{data?.active_employees || 0}</div>
        </Card>
      </div>

      <Card className="overflow-hidden">
        <div className="p-12 text-center text-gray-500">
          No employees found.
        </div>
      </Card>
    </div>
  );
}


