/**
 * Мок-данные по составу команды: фармеры, обработчики, тимлиды.
 *
 * Модели оплаты взяты из статьи «Экономика медиабаинга» (раздел 05):
 *   Медиабайер  — оклад + % от Net Campaign Profit его связок
 *   Тимлид      — оклад + % (override) от прибыли всей команды
 *   Фармер      — фикс + квота (число подготовленных аккаунтов/месяц)
 *   Креатив     — фикс или сдельно (утверждённые единицы)
 *
 * Обработчик (лиды/колл-центр) в статьях отсутствует — модель оплаты
 * за обработанный лид/approve добавлена по логике роли (см. OPEN_QUESTIONS Q15).
 *
 * ВАЖНО: это демо-данные для прототипа. Реальные цифры придут из БД.
 */

import type { StaffRole } from './constants';

// ─── Тимлиды ─────────────────────────────────────────────────────────

export interface TeamLeadInfo {
  id: string;
  name: string;
  team: string;
  /** Сколько человек в подчинении (все роли). */
  headcount: number;
  /** Состав подчинённых по ролям — определяет, что видно в карточке. */
  reports: Partial<Record<StaffRole, number>>;
  teamSpend: number;
  teamRevenue: number;
  teamProfit: number;
  roi: number;
  /** Оклад тимлида. */
  baseSalary: number;
  /** Override-процент от прибыли команды. */
  overridePercent: number;
  /** Начисленный override за период. */
  overrideAmount: number;
  payoutTotal: number;
  trend: 'up' | 'down' | 'neutral';
  flag: string | null;
}

export const teamLeadsData: TeamLeadInfo[] = [
  {
    id: 'tl-1',
    name: 'E. Sokolova',
    team: 'Team Alpha',
    headcount: 5,
    reports: { media_buyer: 2, farmer: 1, processor: 1, creative: 1 },
    teamSpend: 186000,
    teamRevenue: 396000,
    teamProfit: 210000,
    roi: 27,
    baseSalary: 4000,
    overridePercent: 8,
    overrideAmount: 16800,
    payoutTotal: 20800,
    trend: 'down',
    flag: 'ROI на 35% ниже среднего по компании за последние 14 дней',
  },
  {
    id: 'tl-2',
    name: 'R. Kuznetsov',
    team: 'Team Beta',
    headcount: 4,
    reports: { media_buyer: 2, farmer: 1, processor: 1 },
    teamSpend: 214000,
    teamRevenue: 554000,
    teamProfit: 340000,
    roi: 51,
    baseSalary: 4500,
    overridePercent: 8,
    overrideAmount: 27200,
    payoutTotal: 31700,
    trend: 'up',
    flag: null,
  },
  {
    id: 'tl-3',
    name: 'N. Zaytseva',
    team: 'Team Gamma',
    headcount: 3,
    reports: { media_buyer: 1, processor: 1, creative: 1 },
    teamSpend: 121000,
    teamRevenue: 286000,
    teamProfit: 165000,
    roi: 39,
    baseSalary: 3800,
    overridePercent: 7,
    overrideAmount: 11550,
    payoutTotal: 15350,
    trend: 'up',
    flag: null,
  },
];

// ─── Фармеры ─────────────────────────────────────────────────────────

export interface FarmerInfo {
  id: string;
  name: string;
  team: string;
  /** Тимлид, к которому прикреплён сотрудник. */
  teamLead: string;
  /** Квота аккаунтов в месяц (из compensation_plans.quota_target). */
  quotaTarget: number;
  /** Подготовлено за период. */
  accountsPrepared: number;
  /** Из подготовленных — сколько ещё живы. */
  accountsAlive: number;
  /** Забанено. */
  accountsBanned: number;
  /** Средняя продолжительность жизни аккаунта, дней. */
  avgLifespanDays: number;
  /** Стоимость расходников на подготовку (прокси, карты, антидетект). */
  consumablesCost: number;
  baseSalary: number;
  quotaBonus: number;
  payoutTotal: number;
  trend: 'up' | 'down' | 'neutral';
}

export const farmersData: FarmerInfo[] = [
  {
    id: 'fr-1',
    name: 'I. Titov',
    team: 'Team Alpha',
    teamLead: 'E. Sokolova',
    quotaTarget: 40,
    accountsPrepared: 44,
    accountsAlive: 31,
    accountsBanned: 13,
    avgLifespanDays: 18,
    consumablesCost: 2860,
    baseSalary: 3000,
    quotaBonus: 1200,
    payoutTotal: 4200,
    trend: 'up',
  },
  {
    id: 'fr-2',
    name: 'P. Sidorov',
    team: 'Team Beta',
    teamLead: 'R. Kuznetsov',
    quotaTarget: 40,
    accountsPrepared: 38,
    accountsAlive: 29,
    accountsBanned: 9,
    avgLifespanDays: 24,
    consumablesCost: 2470,
    baseSalary: 3000,
    quotaBonus: 0,
    payoutTotal: 3000,
    trend: 'neutral',
  },
  {
    id: 'fr-3',
    name: 'V. Morozov',
    team: 'Team Beta',
    teamLead: 'R. Kuznetsov',
    quotaTarget: 30,
    accountsPrepared: 35,
    accountsAlive: 27,
    accountsBanned: 8,
    avgLifespanDays: 26,
    consumablesCost: 2100,
    baseSalary: 2600,
    quotaBonus: 1000,
    payoutTotal: 3600,
    trend: 'up',
  },
];

// ─── Обработчики (лиды / колл-центр) ─────────────────────────────────

export interface ProcessorInfo {
  id: string;
  name: string;
  team: string;
  teamLead: string;
  /** Вертикаль, на которой работает обработчик. */
  vertical: string;
  /** Получено лидов на обработку. */
  leadsAssigned: number;
  /** Обработано (дозвон/контакт состоялся). */
  leadsProcessed: number;
  /** Подтверждено (approve). */
  leadsApproved: number;
  /** Отклонено/недозвон. */
  leadsRejected: number;
  /** Approve rate, % — ключевая метрика обработчика. */
  approveRate: number;
  /** Выручка, принесённая подтверждёнными лидами. */
  revenueGenerated: number;
  /** Средний чек по подтверждённому лиду. */
  avgOrderValue: number;
  baseSalary: number;
  /** Ставка за подтверждённый лид. */
  ratePerApproved: number;
  bonusAmount: number;
  payoutTotal: number;
  trend: 'up' | 'down' | 'neutral';
}

export const processorsData: ProcessorInfo[] = [
  {
    id: 'pr-1',
    name: 'O. Lebedeva',
    team: 'Team Alpha',
    teamLead: 'E. Sokolova',
    vertical: 'Nutra',
    leadsAssigned: 1420,
    leadsProcessed: 1298,
    leadsApproved: 402,
    leadsRejected: 896,
    approveRate: 31,
    revenueGenerated: 28140,
    avgOrderValue: 70,
    baseSalary: 1200,
    ratePerApproved: 3.5,
    bonusAmount: 1407,
    payoutTotal: 2607,
    trend: 'up',
  },
  {
    id: 'pr-2',
    name: 'T. Yakovlev',
    team: 'Team Beta',
    teamLead: 'R. Kuznetsov',
    vertical: 'Финансовые услуги',
    leadsAssigned: 980,
    leadsProcessed: 934,
    leadsApproved: 355,
    leadsRejected: 579,
    approveRate: 38,
    revenueGenerated: 42600,
    avgOrderValue: 120,
    baseSalary: 1400,
    ratePerApproved: 4,
    bonusAmount: 1420,
    payoutTotal: 2820,
    trend: 'up',
  },
  {
    id: 'pr-3',
    name: 'L. Grishina',
    team: 'Team Gamma',
    teamLead: 'N. Zaytseva',
    vertical: 'Nutra',
    leadsAssigned: 1150,
    leadsProcessed: 921,
    leadsApproved: 202,
    leadsRejected: 719,
    approveRate: 22,
    revenueGenerated: 13130,
    avgOrderValue: 65,
    baseSalary: 1200,
    ratePerApproved: 3.5,
    bonusAmount: 707,
    payoutTotal: 1907,
    trend: 'down',
  },
];

// ─── Рекламные аккаунты (пример «аккаунтов фармеров») ────────────────

export interface AdAccountRow {
  id: string;
  /** Маскированный идентификатор кабинета. */
  externalId: string;
  platform: string;
  status: 'active' | 'warming' | 'banned' | 'suspended';
  /** Фармер, подготовивший аккаунт. */
  preparedBy: string;
  /** Байер, которому передан аккаунт. */
  assignedBuyer: string | null;
  vertical: string;
  geo: string;
  /** Потрачено через этот аккаунт. */
  spend: number;
  /** Сколько дней аккаунт живёт. */
  lifespanDays: number;
  /** Привязанные расходники. */
  consumables: string;
  createdAt: string;
}

export const adAccountsData: AdAccountRow[] = [
  {
    id: 'acc-1',
    externalId: 'act_••••4821',
    platform: 'Meta',
    status: 'active',
    preparedBy: 'I. Titov',
    assignedBuyer: 'D. Volkov',
    vertical: 'iGaming',
    geo: 'EU',
    spend: 42000,
    lifespanDays: 34,
    consumables: 'Proxy mobile · Card ••••4419',
    createdAt: '2026-09-24',
  },
  {
    id: 'acc-2',
    externalId: 'act_••••7735',
    platform: 'Meta',
    status: 'banned',
    preparedBy: 'I. Titov',
    assignedBuyer: 'A. Petrov',
    vertical: 'iGaming',
    geo: 'UK',
    spend: 18400,
    lifespanDays: 11,
    consumables: 'Proxy residential · Card ••••8102',
    createdAt: '2026-10-08',
  },
  {
    id: 'acc-3',
    externalId: 'g-ads-••••2290',
    platform: 'Google',
    status: 'active',
    preparedBy: 'P. Sidorov',
    assignedBuyer: 'M. Ivanova',
    vertical: 'Crypto / prop-trading',
    geo: 'US',
    spend: 36200,
    lifespanDays: 41,
    consumables: 'Proxy datacenter · Card ••••1174',
    createdAt: '2026-09-17',
  },
  {
    id: 'acc-4',
    externalId: 'tt-••••5518',
    platform: 'TikTok',
    status: 'warming',
    preparedBy: 'V. Morozov',
    assignedBuyer: null,
    vertical: 'Nutra',
    geo: 'LATAM',
    spend: 0,
    lifespanDays: 4,
    consumables: 'Proxy mobile · Card ••••9930',
    createdAt: '2026-10-24',
  },
  {
    id: 'acc-5',
    externalId: 'act_••••6027',
    platform: 'Meta',
    status: 'suspended',
    preparedBy: 'P. Sidorov',
    assignedBuyer: 'S. Orlov',
    vertical: 'Nutra',
    geo: 'US',
    spend: 9800,
    lifespanDays: 16,
    consumables: 'Proxy residential · Card ••••3345',
    createdAt: '2026-10-12',
  },
];

// ─── Сводка по ролям для дашборда команды ────────────────────────────

export const staffSummary = {
  media_buyer: { count: 4, label: 'Медиабайеры' },
  team_lead: { count: 3, label: 'Тимлиды' },
  farmer: { count: 3, label: 'Фармеры' },
  processor: { count: 3, label: 'Обработчики' },
  creative: { count: 2, label: 'Креативы' },
};
