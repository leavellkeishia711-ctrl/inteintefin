'use client';

import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui/Card';
import { money } from '@/lib/formatters';
import { Receipt, Plus, Upload, Filter, Search, AlertCircle } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { fetchTransactions } from '@/lib/api';
import { useState } from 'react';
import { TransactionModal } from '@/components/modals/TransactionModal';
import { ImportWizardModal } from '@/components/modals/ImportWizardModal';

export function TransactionsScreen() {
  const t = useTranslations('transactions');
  const [search, setSearch] = useState('');
  const [isTxModalOpen, setIsTxModalOpen] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['transactions', { search }],
    queryFn: () => fetchTransactions({ page: 1, per_page: 50, search }),
  });

  return (
    <div className="space-y-6">
      {isTxModalOpen && <TransactionModal onClose={() => setIsTxModalOpen(false)} />}
      {isImportModalOpen && <ImportWizardModal onClose={() => setIsImportModalOpen(false)} />}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-content-primary">{t('title')}</h1>
          <p className="text-content-secondary mt-1">{t('subtitle')}</p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={() => setIsImportModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-surface text-content-primary border border-border rounded-lg hover:bg-surface-hover transition-colors"
          >
            <Upload className="w-4 h-4" />
            <span>{t('import_csv')}</span>
          </button>
          <button 
            onClick={() => setIsTxModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" />
            <span>{t('add_transaction')}</span>
          </button>
        </div>
      </div>

      <Card className="p-4 flex flex-col md:flex-row gap-4 items-center justify-between bg-surface border-border">
        <div className="flex items-center gap-4 w-full md:w-auto">
          <div className="relative flex-1 md:w-64">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-content-tertiary" />
            <input 
              type="text" 
              placeholder={t('search_placeholder')}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            />
          </div>
          <button className="flex items-center gap-2 px-3 py-2 border border-border rounded-lg text-content-secondary hover:text-content-primary transition-colors">
            <Filter className="w-4 h-4" />
            <span className="text-sm font-medium">{t('filters')}</span>
          </button>
        </div>
        <div className="text-right">
          <p className="text-sm text-content-secondary">{t('total_amount')}</p>
          <p className="text-lg font-semibold text-content-primary">{money(data?.total_amount || 0)}</p>
        </div>
      </Card>

      <Card className="overflow-hidden border-border bg-surface">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-background/50 border-b border-border text-content-secondary">
              <tr>
                <th className="px-6 py-3 font-medium">{t('date')}</th>
                <th className="px-6 py-3 font-medium">{t('type')}</th>
                <th className="px-6 py-3 font-medium">{t('category')}</th>
                <th className="px-6 py-3 font-medium">{t('description')}</th>
                <th className="px-6 py-3 font-medium text-right">{t('amount')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center">
                    <div className="flex flex-col items-center justify-center gap-3">
                      <div className="w-6 h-6 border-2 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
                      <p className="text-content-secondary">{t('loading')}</p>
                    </div>
                  </td>
                </tr>
              ) : isError ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center">
                    <div className="flex flex-col items-center justify-center gap-3 text-red-500">
                      <AlertCircle className="w-8 h-8" />
                      <p>{t('load_error', { message: (error as Error).message })}</p>
                    </div>
                  </td>
                </tr>
              ) : !data?.items || data.items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-16 text-center">
                    <div className="flex flex-col items-center justify-center gap-4 max-w-sm mx-auto">
                      <div className="w-12 h-12 bg-background rounded-full flex items-center justify-center border border-border">
                        <Receipt className="w-6 h-6 text-content-tertiary" />
                      </div>
                      <div>
                        <p className="text-sm text-content-secondary mb-4">{t('no_data')}</p>
                      </div>
                      <div className="flex items-center gap-3 w-full">
                        <button 
                          onClick={() => setIsImportModalOpen(true)}
                          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-surface text-content-primary border border-border rounded-lg hover:bg-surface-hover transition-colors"
                        >
                          <Upload className="w-4 h-4" />
                          <span>{t('import_csv')}</span>
                        </button>
                        <button 
                          onClick={() => setIsTxModalOpen(true)}
                          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors shadow-sm"
                        >
                          <Plus className="w-4 h-4" />
                          <span>{t('add_transaction')}</span>
                        </button>
                      </div>
                    </div>
                  </td>
                </tr>
              ) : (
                data.items.map((tx: any) => (
                  <tr key={tx.id} className="hover:bg-background/50 transition-colors">
                    <td className="px-6 py-4 text-content-primary">{tx.occurred_on}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${tx.type === 'income' ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}`}>
                        {tx.type}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-content-secondary">{tx.category}</td>
                    <td className="px-6 py-4 text-content-primary">{tx.description}</td>
                    <td className="px-6 py-4 text-right font-medium text-content-primary">
                      {money(tx.amount, tx.currency)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}




