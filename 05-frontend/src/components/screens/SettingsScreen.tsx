"use client";

import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui/Card';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { CheckCircle2, XCircle } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';


export default function SettingsScreen() {
  const { data: settingsData } = useQuery({
    queryKey: ['settings'],
    queryFn: () => fetch(process.env.NEXT_PUBLIC_API_URL + '/api/v1/settings', {headers:{'Authorization':'Bearer test'}}).then(res => res.json())
  });
  const t = useTranslations('settings');
  const [locale, setLocale] = useState('en');

  useEffect(() => {
     
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLocale(localStorage.getItem('financeIntel-locale') || 'en');
  }, []);

  const toggleLocale = () => {
    const next = locale === 'en' ? 'ru' : 'en';
    localStorage.setItem('financeIntel-locale', next);
    window.location.reload();
  };

  return (
    <div className="max-w-2xl space-y-6">
      <SectionTitle>{t('title')}</SectionTitle>

      <Card className="p-6">
        <h3 className="font-semibold text-lg mb-4">{t('profile')}</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">{t('compunknownName')}</label>
            <input type="text" disabled value={settingsData?.compunknown_name || 'Loading...'} className="mt-1 block w-full rounded-md border-gray-300 bg-gray-50 shadow-sm sm:text-sm p-2 border" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">{t('currency')}</label>
            <input type="text" disabled value={settingsData?.base_currency || 'Loading...'} className="mt-1 block w-full rounded-md border-gray-300 bg-gray-50 shadow-sm sm:text-sm p-2 border" />
          </div>
        </div>
      </Card>

      <Card className="p-6">
        <h3 className="font-semibold text-lg mb-4">{t('language')}</h3>
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-700">{locale === 'en' ? 'English' : 'Русский'}</span>
          <button onClick={toggleLocale} className="px-4 py-2 bg-teal-600 text-white rounded hover:bg-teal-700 text-sm font-medium transition-colors">
            {t('switch')} {locale === 'en' ? 'RU' : 'EN'}
          </button>
        </div>
      </Card>

      <Card className="p-6">
        <h3 className="font-semibold text-lg mb-4">{t('integrations')}</h3>
        <div className="space-y-3">
          {(settingsData?.integrations || []).map((inv: { id: string, name: string, connected: boolean }) => (
            <div key={inv.id} className="flex items-center justify-between p-3 border rounded-lg bg-gray-50">
              <span className="font-medium">{inv.name}</span>
              {inv.connected ? (
                <div className="flex items-center gap-1 text-green-600 text-sm font-medium"><CheckCircle2 size={16}/> Connected</div>
              ) : (
                <div className="flex items-center gap-1 text-gray-400 text-sm font-medium"><XCircle size={16}/> Not Connected</div>
              )}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}







