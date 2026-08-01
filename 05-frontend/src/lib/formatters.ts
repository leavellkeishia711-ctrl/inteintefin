// Formatters for FinanceIntel
// ESLint rules below strictly forbid float coercion to protect string-based Decimal precision.
 

export const money = (value: string | null | undefined, currency: string = 'USD', locale: string = 'en-US'): string => {
  if (!value) return new Intl.NumberFormat(locale, { style: 'currency', currency }).format(0);
  
  const isNegative = value.startsWith('-');
  const absStr = isNegative ? value.slice(1) : value;
  
  const partsStr = absStr.split('.');
  const integerPart = partsStr[0] || '0';
  const fractionalPart = (partsStr[1] || '00').padEnd(2, '0').slice(0, 2);
  
  let intBig: bigint;
  try {
    intBig = BigInt(isNegative ? '-' + integerPart : integerPart);
  } catch(e) {
    intBig = BigInt(0);
  }

  const formatter = new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  const parts = formatter.formatToParts(intBig);
  return parts.map(p => p.type === 'fraction' ? fractionalPart : p.value).join('');
};

export const moneyCompact = (value: string | null | undefined, currency: string = 'USD', locale: string = 'en-US'): string => {
  if (!value) return new Intl.NumberFormat(locale, { style: 'currency', currency, notation: 'compact' }).format(0);
  
  const isNegative = value.startsWith('-');
  const absStr = isNegative ? value.slice(1) : value;
  const integerPart = absStr.split('.')[0] || '0';
  
  let intBig: bigint;
  try {
    intBig = BigInt(isNegative ? '-' + integerPart : integerPart);
  } catch(e) {
    intBig = BigInt(0);
  }

  // For compact notation, we don't strictly care about exact decimal fraction since it's an approximation unknownway.
  // But to avoid floats completely, we can format the BigInt directly. 
  // Wait, if it's 1.5M, Intl on BigInt does that for us!
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    notation: 'compact',
    compactDisplay: 'short',
    maximumFractionDigits: 1,
  }).format(intBig);
};

export const percent = (value: string | null | undefined, decimals: number = 2, locale: string = 'en-US'): string => {
  if (!value) return '0%';
  const isNegative = value.startsWith('-');
  const absStr = isNegative ? value.slice(1) : value;
  
  const partsStr = absStr.split('.');
  const integerPart = partsStr[0] || '0';
  const fractionalPart = (partsStr[1] || '').padEnd(decimals, '0').slice(0, decimals);
  
  let intBig: bigint;
  try {
    intBig = BigInt(isNegative ? '-' + integerPart : integerPart);
  } catch(e) {
    intBig = BigInt(0);
  }
  
  const formatter = new Intl.NumberFormat(locale, {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  
  const parts = formatter.formatToParts(intBig);
  return parts.map(p => p.type === 'fraction' ? fractionalPart : p.value).join('');
};

export const formatDate = (date: string | Date | null | undefined, locale: string = 'en'): string => {
  if (!date) return '';
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString(locale === 'ru' ? 'ru-RU' : 'en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
};

