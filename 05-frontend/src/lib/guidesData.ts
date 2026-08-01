import React from 'react';
import EkonomikaMediabainga from '@/components/guides/EkonomikaMediabainga';
import RynokArbitrazha from '@/components/guides/RynokArbitrazha';

export interface GuideMeta {
  id: string;
  slug: string;
  title: string;
  description: string;
  component: React.ComponentType;
}

export const guidesData: GuideMeta[] = [
  {
    id: 'g1',
    slug: 'ekonomika-mediabainga',
    title: 'Экономика и финансы медиабаинга',
    description: 'Базовые понятия: выручка, профит, ROI, scrub, hold и кассовые разрывы.',
    component: EkonomikaMediabainga
  },
  {
    id: 'g2',
    slug: 'rynok-arbitrazha-i-performance-marketinga',
    title: 'Рынок арбитража трафика и performance-маркетинга',
    description: 'Из чего состоит рынок, основные вертикали, доли и перспективы.',
    component: RynokArbitrazha
  }
];
