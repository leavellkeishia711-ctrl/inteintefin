"use client";

import React from 'react';
import { Card } from '@/components/ui/Card';
import { BookOpen } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/routing';
import { guidesData } from '@/lib/guidesData';

export default function GuidesScreen() {
  const t = useTranslations('guides');
  const tl = useTranslations('mockLabels');

  return (
    <div className="max-w-2xl">
      <h2 className="text-lg font-semibold text-gray-900 mb-1">{t('title')}</h2>
      <p className="text-sm text-gray-500 mb-6">{t('subtitle')}</p>
      
      <div className="space-y-4">
        {guidesData.map((guide) => (
          <Card key={guide.id} className="p-5 flex items-start gap-4">
            <div className="w-10 h-10 rounded-lg bg-teal-50 text-teal-600 flex items-center justify-center shrink-0">
              <BookOpen size={18} />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-semibold text-gray-900 mb-1">{tl(guide.title)}</h3>
              <p className="text-xs text-gray-500 mb-3 leading-relaxed">{tl(guide.description)}</p>
              <Link 
                href={`/guides/${guide.slug}`}
                className="inline-flex items-center gap-1.5 text-sm font-medium text-teal-600 hover:text-teal-700"
              >
                {t('readArticle')} &rarr;
              </Link>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
