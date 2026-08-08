import { describe, it, expect } from 'vitest';
import { formatMoney, moneyCompact, percent } from './formatters';

describe('formatMoney', () => {
  it('formats positive numbers correctly', () => {
    expect(formatMoney('1234.56', 'USD', 'en-US')).toBe('$1,234.56');
    expect(formatMoney('1234', 'USD', 'en-US')).toBe('$1,234.00');
  });

  it('formats negative numbers correctly', () => {
    expect(formatMoney('-1234.56', 'USD', 'en-US')).toBe('-$1,234.56');
    expect(formatMoney('-0.50', 'USD', 'en-US')).toBe('-$0.50');
  });

  it('formats zero correctly', () => {
    expect(formatMoney('0', 'USD', 'en-US')).toBe('$0.00');
    expect(formatMoney('0.00', 'USD', 'en-US')).toBe('$0.00');
    expect(formatMoney(null, 'USD', 'en-US')).toBe('$0.00');
    expect(formatMoney(undefined, 'USD', 'en-US')).toBe('$0.00');
  });

  it('preserves up to 4 decimal places without precision loss', () => {
    expect(formatMoney('1234.5678', 'USD', 'en-US')).toBe('$1,234.5678');
    expect(formatMoney('-1234.5678', 'USD', 'en-US')).toBe('-$1,234.5678');
    expect(formatMoney('1234.567', 'USD', 'en-US')).toBe('$1,234.567');
  });

  it('handles very large numbers safely using BigInt', () => {
    expect(formatMoney('9999999999999999999.99', 'USD', 'en-US')).toBe('$9,999,999,999,999,999,999.99');
    expect(formatMoney('-9999999999999999999.1234', 'USD', 'en-US')).toBe('-$9,999,999,999,999,999,999.1234');
  });
});

describe('moneyCompact', () => {
  it('formats large positive numbers correctly', () => {
    // Exact output depends on node Intl, but typically $1.5M for 1500000
    const val = moneyCompact('1500000', 'USD', 'en-US');
    expect(val).toMatch(/\$1\.5M/);
  });

  it('formats large negative numbers correctly', () => {
    const val = moneyCompact('-2500000', 'USD', 'en-US');
    expect(val).toMatch(/-\$2\.5M/);
  });
});

describe('percent', () => {
  it('formats positive and negative correctly', () => {
    expect(percent('0.1534', 2, 'en-US')).toBe('0.15%');
    expect(percent('-0.1534', 2, 'en-US')).toBe('-0.15%');
  });
});
