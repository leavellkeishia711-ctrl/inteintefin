import React from 'react';
import { notFound } from 'next/navigation';
import { guidesData } from '@/lib/guidesData';

interface PageProps {
  params: Promise<{ slug: string, locale: string }>;
}

export default async function GuidePage({ params }: PageProps) {
  const resolvedParams = await params;
  const guide = guidesData.find((g) => g.slug === resolvedParams.slug);

  if (!guide) {
    notFound();
  }

  const GuideComponent = guide.component;

  return (
    <>
      {resolvedParams.locale !== 'ru' && (
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-3 text-center text-sm text-amber-800 font-medium">
          Note: This knowledge base article is currently only available in Russian. Translation is in progress.
        </div>
      )}
      <GuideComponent />
    </>
  );
}
