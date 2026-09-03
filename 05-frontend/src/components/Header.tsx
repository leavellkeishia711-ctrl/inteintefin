"use client";

import React, { useState } from 'react';
import { Calendar, ChevronDown, Bell, Globe } from 'lucide-react';
import { usePathname, useRouter } from '@/i18n/routing';
import { useLocale, useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';

interface HeaderProps {
  title?: string;
}

export const Header: React.FC<HeaderProps> = ({ title }) => {
  const tNav = useTranslations('nav');
  const tMock = useTranslations('mock');
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const [langOpen, setLangOpen] = useState(false);
  const { data: user } = useQuery({
    queryKey: ['currentUser'],
    queryFn: () => api.get('/api/v1/auth/me'),
  });

  const getInitials = (email?: string) => {
    if (!email) return 'U';
    return email.substring(0, 2).toUpperCase();
  };

  const switchLocale = (newLocale: string) => {
    // 1. Set cookie for next-intl
    document.cookie = `NEXT_LOCALE=${newLocale}; path=/; max-age=31536000`;
    // 2. Mock API call to save user preference
    api.post('/api/user/preferences', { preferred_language: newLocale })
      .catch(() => {}); // ignore for now as backend is not connected
    
    // 3. Navigate
    router.replace(pathname, { locale: newLocale });
    setLangOpen(false);
  };

  return (
    <header className="h-16 border-b border-gray-200 bg-white px-8 flex items-center justify-between sticky top-0 z-10 shrink-0">
      <div>
        <h2 className="font-semibold text-gray-900">{title || tNav('dashboard')}</h2>
        <span className="text-xs text-gray-400">{tMock('dateRange')}</span>
      </div>
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 px-3 py-1.5 rounded-md border border-gray-200 cursor-pointer hover:border-gray-300 transition-colors">
          <Calendar size={14} />
          {tMock('month')}
          <ChevronDown size={14} className="text-gray-400" />
        </div>
        
        <div className="relative">
          <button 
            onClick={() => setLangOpen(!langOpen)}
            className="flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900 transition-colors"
          >
            <Globe size={18} />
            <span className="uppercase font-medium">{locale}</span>
          </button>
          {langOpen && (
            <div className="absolute top-full right-0 mt-2 w-32 bg-white rounded-lg shadow-lg border border-gray-100 py-1 z-50">
              <button 
                onClick={() => switchLocale('en')}
                className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-50 ${locale === 'en' ? 'text-teal-600 font-medium' : 'text-gray-700'}`}
              >
                English
              </button>
              <button 
                onClick={() => switchLocale('ru')}
                className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-50 ${locale === 'ru' ? 'text-teal-600 font-medium' : 'text-gray-700'}`}
              >
                Русский
              </button>
            </div>
          )}
        </div>

        <button className="text-gray-400 hover:text-gray-900 transition-colors">
          <Bell size={20} />
        </button>
        <div className="w-8 h-8 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center font-semibold text-sm cursor-pointer" title={user?.email}>
          {getInitials(user?.email)}
        </div>
      </div>
    </header>
  );
};
