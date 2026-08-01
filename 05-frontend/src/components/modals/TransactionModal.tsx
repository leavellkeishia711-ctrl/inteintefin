import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createTransaction } from '@/lib/api/client';
import { X, Loader2 } from 'lucide-react';

interface Props {
  onClose: () => void;
}

export function TransactionModal({ onClose }: Props) {
  const t = useTranslations('transactions');
  const queryClient = useQueryClient();
  
  const [formData, setFormData] = useState({
    amount: '',
    currency: 'USD',
    type: 'expense',
    category: 'ad_spend',
    occurred_on: new Date().toISOString().split('T')[0],
    description: '',
  });

  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => createTransaction(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      onClose();
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate({
      ...formData,
      amount: formData.amount
    });
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-surface rounded-xl shadow-xl border border-border w-full max-w-md overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-lg font-semibold text-content-primary">{t('add_transaction')}</h2>
          <button onClick={onClose} className="text-content-secondary hover:text-content-primary">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-sm font-medium text-content-secondary">{t('amount')}</label>
              <input
                type="number"
                step="0.01"
                required
                value={formData.amount}
                onChange={e => setFormData({...formData, amount: e.target.value})}
                className="w-full px-3 py-2 bg-background border border-border rounded-lg text-content-primary focus:outline-none focus:ring-2 focus:ring-primary-500/50"
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-content-secondary">Currency</label>
              <select
                value={formData.currency}
                onChange={e => setFormData({...formData, currency: e.target.value})}
                className="w-full px-3 py-2 bg-background border border-border rounded-lg text-content-primary focus:outline-none focus:ring-2 focus:ring-primary-500/50"
              >
                <option value="USD">USD</option>
                <option value="EUR">EUR</option>
                <option value="RUB">RUB</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-sm font-medium text-content-secondary">{t('type')}</label>
              <select
                value={formData.type}
                onChange={e => setFormData({...formData, type: e.target.value})}
                className="w-full px-3 py-2 bg-background border border-border rounded-lg text-content-primary focus:outline-none focus:ring-2 focus:ring-primary-500/50"
              >
                <option value="expense">Expense</option>
                <option value="income">Income</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-content-secondary">{t('category')}</label>
              <select
                value={formData.category}
                onChange={e => setFormData({...formData, category: e.target.value})}
                className="w-full px-3 py-2 bg-background border border-border rounded-lg text-content-primary focus:outline-none focus:ring-2 focus:ring-primary-500/50"
              >
                <option value="ad_spend">Ad Spend</option>
                <option value="revenue">Revenue</option>
                <option value="consumables">Consumables</option>
                <option value="salary">Salary</option>
                <option value="software">Software</option>
                <option value="tax">Tax</option>
              </select>
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium text-content-secondary">{t('date')}</label>
            <input
              type="date"
              required
              value={formData.occurred_on}
              onChange={e => setFormData({...formData, occurred_on: e.target.value})}
              className="w-full px-3 py-2 bg-background border border-border rounded-lg text-content-primary focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            />
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium text-content-secondary">{t('description')}</label>
            <input
              type="text"
              value={formData.description}
              onChange={e => setFormData({...formData, description: e.target.value})}
              className="w-full px-3 py-2 bg-background border border-border rounded-lg text-content-primary focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            />
          </div>

          {mutation.isError && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-500 text-sm">
              {(mutation.error as Error).message}
            </div>
          )}

          <div className="pt-4 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-border text-content-secondary rounded-lg hover:text-content-primary transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50"
            >
              {mutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}



