import { TransactionsScreen } from '@/components/screens/TransactionsScreen';
import { getTranslations } from 'next-intl/server';
import { setRequestLocale } from 'next-intl/server';

export async function generateMetadata({ params: { locale } }: { params: { locale: string } }) {
  const t = await getTranslations({ locale, namespace: 'transactions' });
  return {
    title: t('title') + ' | FinanceIntel',
  };
}

export default function TransactionsPage({ params: { locale } }: { params: { locale: string } }) {
  setRequestLocale(locale);
  return <TransactionsScreen />;
}
