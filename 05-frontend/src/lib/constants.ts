/**
 * РЎРїСЂР°РІРѕС‡РЅРёРєРё РґР»СЏ С„РёР»СЊС‚СЂРѕРІ Рё СЃРµР»РµРєС‚РѕРІ.
 *
 * РСЃС‚РѕС‡РЅРёРєРё (СЃРј. 02-product-docs/):
 *  - Р’РµСЂС‚РёРєР°Р»Рё: СЃС‚Р°С‚СЊСЏ В«Р С‹РЅРѕРє Р°СЂР±РёС‚СЂР°Р¶Р° Рё performance-РјР°СЂРєРµС‚РёРЅРіР°В» (СЂР°Р·РґРµР» 02, РґРѕР»Рё СЂС‹РЅРєР°).
 *  - Р РѕР»Рё Рё РјРѕРґРµР»Рё РѕРїР»Р°С‚С‹: СЃС‚Р°С‚СЊСЏ В«Р­РєРѕРЅРѕРјРёРєР° РјРµРґРёР°Р±Р°РёРЅРіР°В» (СЂР°Р·РґРµР» 05, С‚Р°Р±Р»РёС†Р° РєРѕРјРїРµРЅСЃР°С†РёР№).
 *  - РўСЂРµРєРµСЂС‹/РїСЂРѕРєСЃРё: В«Р­РєРѕРЅРѕРјРёРєР° РјРµРґРёР°Р±Р°РёРЅРіР°В», СЂР°Р·РґРµР» 03 (РёРЅС„СЂР°СЃС‚СЂСѓРєС‚СѓСЂР°).
 *
 * вљ пёЏ Р“РµРѕ Рё РёСЃС‚РѕС‡РЅРёРєРё С‚СЂР°С„РёРєР° РІ СЃС‚Р°С‚СЊСЏС… РЅРµ РїРµСЂРµС‡РёСЃР»РµРЅС‹ вЂ” СЃРїРёСЃРєРё РЅРёР¶Рµ СЃРѕР±СЂР°РЅС‹
 * РёР· РѕР±С‰РµРїСЂРёРЅСЏС‚РѕР№ РїСЂР°РєС‚РёРєРё Рё РїРѕРјРµС‡РµРЅС‹ РєР°Рє С‚СЂРµР±СѓСЋС‰РёРµ РїРѕРґС‚РІРµСЂР¶РґРµРЅРёСЏ (СЃРј. OPEN_QUESTIONS.md).
 */

// в”Ђв”Ђв”Ђ Р’РµСЂС‚РёРєР°Р»Рё в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
// Р”РѕР»Рё СЂС‹РЅРєР° РїРѕ affiliate-Р±СЋРґР¶РµС‚Сѓ РёР· СЃС‚Р°С‚СЊРё РїСЂРѕ СЂС‹РЅРѕРє (СЂР°Р·РґРµР» 02).
export const VERTICALS = [
  { value: 'ecommerce', label: 'eCommerce', marketShare: 38 },
  { value: 'igaming', label: 'iGaming / Gambling', marketShare: 22 },
  { value: 'finance', label: 'Р¤РёРЅР°РЅСЃРѕРІС‹Рµ СѓСЃР»СѓРіРё', marketShare: 15 },
  { value: 'b2b_saas', label: 'B2B SaaS', marketShare: 9 },
  { value: 'crypto', label: 'Crypto / prop-trading', marketShare: 4 },
  { value: 'nutra', label: 'Nutra', marketShare: null },
  { value: 'dating', label: 'Dating', marketShare: null },
  { value: 'sweeps', label: 'Sweepstakes', marketShare: null },
  { value: 'other', label: 'РџСЂРѕС‡РµРµ', marketShare: null },
] as const;

export type VerticalValue = (typeof VERTICALS)[number]['value'];

/** Р’РµСЂС‚РёРєР°Р»Рё, РѕС‚РјРµС‡РµРЅРЅС‹Рµ РїР»Р°С‚С„РѕСЂРјР°РјРё РєР°Рє РІС‹СЃРѕРєРѕСЂРёСЃРєРѕРІС‹Рµ (В«Р­РєРѕРЅРѕРјРёРєР° РјРµРґРёР°Р±Р°РёРЅРіР°В», СЂР°Р·РґРµР» 04). */
export const HIGH_RISK_VERTICALS: VerticalValue[] = ['igaming', 'crypto', 'nutra'];

// в”Ђв”Ђв”Ђ Р“РµРѕ в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
// вљ пёЏ Р’ СЃС‚Р°С‚СЊСЏС… РЅРµС‚ СЃРїРёСЃРєР° РіРµРѕ. РўСЂРµР±СѓРµС‚ РїРѕРґС‚РІРµСЂР¶РґРµРЅРёСЏ.
export const GEOS = [
  { value: 'us', label: 'US', tier: 1 },
  { value: 'uk', label: 'UK', tier: 1 },
  { value: 'ca', label: 'Canada', tier: 1 },
  { value: 'au', label: 'Australia', tier: 1 },
  { value: 'de', label: 'Germunknown', tier: 1 },
  { value: 'eu', label: 'EU (РїСЂРѕС‡РёРµ)', tier: 1 },
  { value: 'latam', label: 'LATAM', tier: 2 },
  { value: 'br', label: 'Brazil', tier: 2 },
  { value: 'mx', label: 'Mexico', tier: 2 },
  { value: 'in', label: 'India', tier: 3 },
  { value: 'sea', label: 'SEA', tier: 3 },
  { value: 'cis', label: 'CIS', tier: 2 },
  { value: 'other', label: 'РџСЂРѕС‡РёРµ', tier: null },
] as const;

// в”Ђв”Ђв”Ђ РџР»Р°С‚С„РѕСЂРјС‹ / РёСЃС‚РѕС‡РЅРёРєРё С‚СЂР°С„РёРєР° в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
// вљ пёЏ Р’ СЃС‚Р°С‚СЊСЏС… РЅРµС‚ СЃРїРёСЃРєР° РёСЃС‚РѕС‡РЅРёРєРѕРІ. РўСЂРµР±СѓРµС‚ РїРѕРґС‚РІРµСЂР¶РґРµРЅРёСЏ.
export const PLATFORMS = [
  { value: 'meta', label: 'Meta Ads' },
  { value: 'google', label: 'Google Ads' },
  { value: 'tiktok', label: 'TikTok Ads' },
  { value: 'uac', label: 'Google UAC' },
  { value: 'push', label: 'Push-СЃРµС‚Рё' },
  { value: 'inapp', label: 'In-App' },
  { value: 'native', label: 'Native' },
  { value: 'seo', label: 'SEO' },
  { value: 'influence', label: 'Influence' },
  { value: 'other', label: 'РџСЂРѕС‡РµРµ' },
] as const;

// в”Ђв”Ђв”Ђ РњРѕРґРµР»Рё РІС‹РїР»Р°С‚ РїРѕ РѕС„С„РµСЂР°Рј в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
// РР· СЃС‚Р°С‚РµР№ СѓРїРѕРјРёРЅР°СЋС‚СЃСЏ CPA, RevShare Рё РіРёР±СЂРёРґ. РћСЃС‚Р°Р»СЊРЅС‹Рµ вЂ” РїСЂР°РєС‚РёРєР°.
export const PAYOUT_MODELS = [
  { value: 'cpa', label: 'CPA' },
  { value: 'revshare', label: 'RevShare' },
  { value: 'hybrid', label: 'Р“РёР±СЂРёРґ (CPA + RevShare)' },
  { value: 'cpl', label: 'CPL' },
  { value: 'cps', label: 'CPS' },
] as const;

// в”Ђв”Ђв”Ђ Р¦РёРєР» РІС‹РїР»Р°С‚ РѕС‚ РїР°СЂС‚РЅС‘СЂРєРё в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
// В«Р­РєРѕРЅРѕРјРёРєР° РјРµРґРёР°Р±Р°РёРЅРіР°В», СЂР°Р·РґРµР» 02.
export const PAYMENT_TERMS = [
  { value: 'net30', label: 'Net-30' },
  { value: 'net15', label: 'Net-15' },
  { value: 'net7', label: 'Net-7' },
  { value: 'weekly', label: 'Weekly / Net-5' },
] as const;

// в”Ђв”Ђв”Ђ Р РѕР»Рё СЃРѕС‚СЂСѓРґРЅРёРєРѕРІ в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
/**
 * `staffRole` вЂ” РїСЂРѕРёР·РІРѕРґСЃС‚РІРµРЅРЅР°СЏ СЂРѕР»СЊ (РґР»СЏ Р°РЅР°Р»РёС‚РёРєРё Рё Р·Р°СЂРїР»Р°С‚).
 * РћС‚Р»РёС‡Р°РµС‚СЃСЏ РѕС‚ `role` РІ users (РїСЂР°РІР° РґРѕСЃС‚СѓРїР°: owner/cfo/team_lead/...).
 *
 * `optional: true` вЂ” СЂРѕР»СЊ РµСЃС‚СЊ РЅРµ Сѓ РєР°Р¶РґРѕР№ РєРѕРјРїР°РЅРёРё. Р¤СѓРЅРєС†РёРѕРЅР°Р» РїРѕРґ С‚Р°РєСѓСЋ
 * СЂРѕР»СЊ СЃРєСЂС‹РІР°РµС‚СЃСЏ, РїРѕРєР° РІ РєРѕРјРїР°РЅРёРё РЅРµС‚ РЅРё РѕРґРЅРѕРіРѕ СЃРѕС‚СЂСѓРґРЅРёРєР° СЃ РЅРµР№.
 */
export const STAFF_ROLES = [
  {
    value: 'media_buyer',
    label: 'РњРµРґРёР°Р±Р°Р№РµСЂ',
    optional: false,
    compensation: 'РћРєР»Р°Рґ + % РѕС‚ РїСЂРёР±С‹Р»Рё',
    variableBasis: 'Net Campaign Profit РµРіРѕ СЃРІСЏР·РѕРє',
  },
  {
    value: 'team_lead',
    label: 'РўРёРјР»РёРґ',
    optional: true,
    compensation: 'РћРєР»Р°Рґ + % (override)',
    variableBasis: 'РџСЂРёР±С‹Р»СЊ РІСЃРµР№ РєРѕРјР°РЅРґС‹',
  },
  {
    value: 'farmer',
    label: 'Р¤Р°СЂРјРµСЂ',
    optional: true,
    compensation: 'Р¤РёРєСЃ + РєРІРѕС‚Р°',
    variableBasis: 'Р§РёСЃР»Рѕ РїРѕРґРіРѕС‚РѕРІР»РµРЅРЅС‹С… Р°РєРєР°СѓРЅС‚РѕРІ/РјРµСЃСЏС†',
  },
  {
    value: 'processor',
    label: 'РћР±СЂР°Р±РѕС‚С‡РёРє',
    optional: true,
    compensation: 'Р¤РёРєСЃ + % / Р·Р° Р»РёРґ',
    variableBasis: 'РћР±СЂР°Р±РѕС‚Р°РЅРЅС‹Рµ Р»РёРґС‹ Рё approve rate',
  },
  {
    value: 'creative',
    label: 'РљСЂРµР°С‚РёРІ / РјРѕРЅС‚Р°Р¶',
    optional: true,
    compensation: 'Р¤РёРєСЃ РёР»Рё СЃРґРµР»СЊРЅРѕ',
    variableBasis: 'РћР±СЉС‘Рј Рё СѓС‚РІРµСЂР¶РґС‘РЅРЅС‹Рµ РµРґРёРЅРёС†С‹',
  },
] as const;

export type StaffRole = (typeof STAFF_ROLES)[number]['value'];

/** Р РѕР»Рё, РЅР°Р»РёС‡РёРµ РєРѕС‚РѕСЂС‹С… РІРєР»СЋС‡Р°РµС‚ СЃРѕРѕС‚РІРµС‚СЃС‚РІСѓСЋС‰РёР№ С„СѓРЅРєС†РёРѕРЅР°Р». */
export const OPTIONAL_STAFF_ROLES = STAFF_ROLES.filter((r) => r.optional).map((r) => r.value);

// в”Ђв”Ђв”Ђ РЎС‚Р°С‚СѓСЃС‹ СЂРµРєР»Р°РјРЅС‹С… Р°РєРєР°СѓРЅС‚РѕРІ в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
export const AD_ACCOUNT_STATUSES = [
  { value: 'warming', label: 'РџСЂРѕРіСЂРµРІ' },
  { value: 'active', label: 'РђРєС‚РёРІРµРЅ' },
  { value: 'suspended', label: 'РћРіСЂР°РЅРёС‡РµРЅ' },
  { value: 'banned', label: 'Р—Р°Р±Р°РЅРµРЅ' },
] as const;

// в”Ђв”Ђв”Ђ РЎС‚Р°С‚СѓСЃС‹ Р»РёРґРѕРІ (РґР»СЏ РѕР±СЂР°Р±РѕС‚С‡РёРєРѕРІ) в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
export const LEAD_STATUSES = [
  { value: 'new', label: 'РќРѕРІС‹Р№' },
  { value: 'in_progress', label: 'Р’ СЂР°Р±РѕС‚Рµ' },
  { value: 'approved', label: 'РџРѕРґС‚РІРµСЂР¶РґС‘РЅ' },
  { value: 'rejected', label: 'РћС‚РєР»РѕРЅС‘РЅ' },
  { value: 'trash', label: 'РўСЂРµС€' },
] as const;

// в”Ђв”Ђв”Ђ РўРёРїС‹ СЂР°СЃС…РѕРґРЅРёРєРѕРІ в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
// В«Р­РєРѕРЅРѕРјРёРєР° РјРµРґРёР°Р±Р°РёРЅРіР°В», СЂР°Р·РґРµР» 03.
export const CONSUMABLE_TYPES = [
  { value: 'proxy', label: 'Прокси' },
  { value: 'card', label: 'Карта' },
  { value: 'account_service', label: 'Сервис аккаунтов' },
  { value: 'other', label: 'Прочее' },
] as const;

// в”Ђв”Ђв”Ђ РҐРµР»РїРµСЂС‹ в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
export const verticalLabel = (value: string) =>
  VERTICALS.find((v) => v.value === value)?.label ?? value;

export const geoLabel = (value: string) => GEOS.find((g) => g.value === value)?.label ?? value;

export const platformLabel = (value: string) =>
  PLATFORMS.find((p) => p.value === value)?.label ?? value;

export const staffRoleLabel = (value: string) =>
  STAFF_ROLES.find((r) => r.value === value)?.label ?? value;

// в”Ђв”Ђв”Ђ РџР°СЂС‚РЅС‘СЂСЃРєРёРµ РІС‹РїР»Р°С‚С‹ Рё С…РѕР»РґС‹ в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
export const PAYOUT_STATUSES = [
  { value: 'booked', label: 'Booked', tone: 'neutral' },
  { value: 'in_hold', label: 'In Hold', tone: 'warning' },
  { value: 'scrubbed', label: 'Scrubbed', tone: 'danger' },
  { value: 'paid', label: 'Paid', tone: 'ok' },
] as const;

export type PayoutStatus = (typeof PAYOUT_STATUSES)[number]['value'];

// РР· СЃС‚Р°С‚СЊРё "Р­РєРѕРЅРѕРјРёРєР° РјРµРґРёР°Р±Р°РёРЅРіР°"
export const HOLD_PERIODS_BY_VERTICAL: Record<string, { min: number, max: number } | null> = {
  igaming: { min: 30, max: 45 },
  nutra: { min: 25, max: 35 },
  crypto: { min: 14, max: 30 },
  // вљ пёЏ Р”РѕРїСѓС‰РµРЅРёРµ: СЃС‚Р°РЅРґР°СЂС‚РЅС‹Р№ С…РѕР»Рґ РґР»СЏ РЅРµ СѓРїРѕРјСЏРЅСѓС‚С‹С… РІ СЃС‚Р°С‚СЊРµ РІРµСЂС‚РёРєР°Р»РµР№
  ecommerce: { min: 14, max: 30 },
  finance: { min: 14, max: 30 },
  b2b_saas: { min: 30, max: 45 },
  dating: { min: 14, max: 30 },
  sweeps: { min: 14, max: 30 },
  other: { min: 14, max: 30 },
};

// РР· СЃС‚Р°С‚СЊРё "Р­РєРѕРЅРѕРјРёРєР° РјРµРґРёР°Р±Р°РёРЅРіР°"
export const TYPICAL_SCRUB_BY_VERTICAL: Record<string, { min: number, max: number } | null> = {
  igaming: { min: 10, max: 30 },
  nutra: { min: 10, max: 30 },
  crypto: null, // РќРµС‚ РґР°РЅРЅС‹С… РІ СЃС‚Р°С‚СЊРµ
  ecommerce: null,
  finance: null,
  b2b_saas: null,
  dating: null,
  sweeps: null,
  other: null,
};

// вљ пёЏ Р”РµРјРѕ-СЃРїРёСЃРѕРє РїР°СЂС‚РЅС‘СЂРѕРє. РўСЂРµР±СѓРµС‚ РїРѕРґС‚РІРµСЂР¶РґРµРЅРёСЏ СЃ РїРёР»РѕС‚РЅС‹РјРё РєР»РёРµРЅС‚Р°РјРё.
export const AFFILIATE_NETWORKS = [
  { value: 'network_a', label: 'Network A' },
  { value: 'leadrock', label: 'LeadRock Demo' },
  { value: 'adcombo', label: 'AdCombo Demo' },
  { value: 'affise_demo', label: 'Affise Internal' },
  { value: 'crypto_net', label: 'CryptoNet X' },
] as const;

export const payoutStatusLabel = (value: string) =>
  PAYOUT_STATUSES.find((s) => s.value === value)?.label ?? value;

export const networkLabel = (value: string) =>
  AFFILIATE_NETWORKS.find((n) => n.value === value)?.label ?? value;

