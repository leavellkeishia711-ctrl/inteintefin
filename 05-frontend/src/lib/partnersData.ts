import { PayoutStatus } from './constants';

export interface AffiliateNetworkInfo {
  id: string;
  name: string;
  paymentTerms: string;
  payoutModel: string;
  verticals: string[];
  booked: number;
  inHold: number;
  approved: number;
  paid: number;
  scrubbed: number;
  clawback: number;
  netConfirmed: number;
  scrubRate: number;
  avgHoldDays: number;
  nextPaymentDate: string | null;
  trend: 'up' | 'down' | 'neutral';
  flag: string | null;
}

export interface PayoutRecord {
  id: string;
  networkId: string;
  networkName: string;
  vertical: string;
  geo: string;
  campaignName: string;
  buyer: string;
  amount: number;
  status: PayoutStatus;
  bookedOn: string;
  holdUntil: string | null;
  daysInHold: number | null; // Negative means overdue
  paidOn: string | null;
  paymentTerms: string;
  note: string | null;
}

export const networksData: AffiliateNetworkInfo[] = [
  {
    id: 'network_a',
    name: 'Network A',
    paymentTerms: 'net30',
    payoutModel: 'cpa',
    verticals: ['igaming', 'crypto'],
    booked: 450000,
    inHold: 120000,
    approved: 80000,
    paid: 205000,
    scrubbed: 40000,
    clawback: 5000,
    netConfirmed: 285000,
    scrubRate: 8.8,
    avgHoldDays: 32,
    nextPaymentDate: '2026-08-15',
    trend: 'up',
    flag: null,
  },
  {
    id: 'leadrock',
    name: 'LeadRock Demo',
    paymentTerms: 'net15',
    payoutModel: 'cpa',
    verticals: ['nutra', 'ecommerce'],
    booked: 210000,
    inHold: 45000,
    approved: 10000,
    paid: 125000,
    scrubbed: 30000,
    clawback: 0,
    netConfirmed: 135000,
    scrubRate: 14.2,
    avgHoldDays: 18,
    nextPaymentDate: '2026-08-05',
    trend: 'neutral',
    flag: null,
  },
  {
    id: 'adcombo',
    name: 'AdCombo Demo',
    paymentTerms: 'net7',
    payoutModel: 'cpa',
    verticals: ['nutra', 'sweeps'],
    booked: 180000,
    inHold: 20000,
    approved: 15000,
    paid: 82000,
    scrubbed: 63000,
    clawback: 0,
    netConfirmed: 97000,
    scrubRate: 35.0, // Аномальный скраб
    avgHoldDays: 8,
    nextPaymentDate: '2026-08-02',
    trend: 'down',
    flag: 'High scrub rate: 35% vs typical 10-30%',
  },
  {
    id: 'affise_demo',
    name: 'Affise Internal',
    paymentTerms: 'net30',
    payoutModel: 'revshare',
    verticals: ['igaming', 'dating'],
    booked: 95000,
    inHold: 55000,
    approved: 0,
    paid: 30000,
    scrubbed: 10000,
    clawback: 0,
    netConfirmed: 30000,
    scrubRate: 10.5,
    avgHoldDays: 35,
    nextPaymentDate: '2026-08-25',
    trend: 'up',
    flag: 'Overdue holds present', // Просроченный холд
  },
  {
    id: 'crypto_net',
    name: 'CryptoNet X',
    paymentTerms: 'weekly',
    payoutModel: 'hybrid',
    verticals: ['crypto'],
    booked: 45000,
    inHold: 10000,
    approved: 5000,
    paid: 28000,
    scrubbed: 1000,
    clawback: 1000, // Клоубэк
    netConfirmed: 33000,
    scrubRate: 2.2,
    avgHoldDays: 15,
    nextPaymentDate: '2026-07-31',
    trend: 'up',
    flag: null,
  },
];

export const payoutsData: PayoutRecord[] = [
  // Network A
  { id: 'p1', networkId: 'network_a', networkName: 'Network A', vertical: 'igaming', geo: 'eu', campaignName: 'EU_Slots_Broad', buyer: 'Alex M.', amount: 50000, status: 'paid', bookedOn: '2026-05-15', holdUntil: '2026-06-15', daysInHold: null, paidOn: '2026-06-20', paymentTerms: 'net30', note: null },
  { id: 'p2', networkId: 'network_a', networkName: 'Network A', vertical: 'igaming', geo: 'de', campaignName: 'DE_Casino_Search', buyer: 'Sarah T.', amount: 30000, status: 'approved', bookedOn: '2026-06-20', holdUntil: '2026-07-20', daysInHold: 0, paidOn: null, paymentTerms: 'net30', note: 'Awaiting invoice payment' },
  { id: 'p3', networkId: 'network_a', networkName: 'Network A', vertical: 'crypto', geo: 'uk', campaignName: 'UK_Crypto_Native', buyer: 'Alex M.', amount: 80000, status: 'pending', bookedOn: '2026-07-10', holdUntil: '2026-08-10', daysInHold: 13, paidOn: null, paymentTerms: 'net30', note: null },
  { id: 'p4', networkId: 'network_a', networkName: 'Network A', vertical: 'igaming', geo: 'ca', campaignName: 'CA_Slots_Retargeting', buyer: 'Mike R.', amount: 15000, status: 'scrubbed', bookedOn: '2026-06-01', holdUntil: null, daysInHold: null, paidOn: null, paymentTerms: 'net30', note: 'Duplicate leads rejected' },
  { id: 'p5', networkId: 'network_a', networkName: 'Network A', vertical: 'crypto', geo: 'au', campaignName: 'AU_Trading_FB', buyer: 'Sarah T.', amount: 5000, status: 'clawback', bookedOn: '2026-04-10', holdUntil: '2026-05-10', daysInHold: null, paidOn: '2026-05-15', paymentTerms: 'net30', note: 'Fraud flag detected post-payment' },
  
  // LeadRock Demo
  { id: 'p6', networkId: 'leadrock', networkName: 'LeadRock Demo', vertical: 'nutra', geo: 'us', campaignName: 'US_WeightLoss_TikTok', buyer: 'Elena V.', amount: 45000, status: 'paid', bookedOn: '2026-06-05', holdUntil: '2026-06-30', daysInHold: null, paidOn: '2026-07-05', paymentTerms: 'net15', note: null },
  { id: 'p7', networkId: 'leadrock', networkName: 'LeadRock Demo', vertical: 'ecommerce', geo: 'uk', campaignName: 'UK_Gadgets_Google', buyer: 'David K.', amount: 10000, status: 'approved', bookedOn: '2026-07-01', holdUntil: '2026-07-15', daysInHold: null, paidOn: null, paymentTerms: 'net15', note: null },
  { id: 'p8', networkId: 'leadrock', networkName: 'LeadRock Demo', vertical: 'nutra', geo: 'br', campaignName: 'BR_Health_FB', buyer: 'Elena V.', amount: 25000, status: 'pending', bookedOn: '2026-07-15', holdUntil: '2026-08-15', daysInHold: 18, paidOn: null, paymentTerms: 'net15', note: null },
  { id: 'p9', networkId: 'leadrock', networkName: 'LeadRock Demo', vertical: 'nutra', geo: 'mx', campaignName: 'MX_Beauty_Insta', buyer: 'David K.', amount: 15000, status: 'scrubbed', bookedOn: '2026-06-25', holdUntil: null, daysInHold: null, paidOn: null, paymentTerms: 'net15', note: 'Quality check failed' },

  // AdCombo Demo (High Scrub)
  { id: 'p10', networkId: 'adcombo', networkName: 'AdCombo Demo', vertical: 'nutra', geo: 'latam', campaignName: 'LATAM_Diet_Push', buyer: 'Mike R.', amount: 42000, status: 'paid', bookedOn: '2026-07-01', holdUntil: '2026-07-08', daysInHold: null, paidOn: '2026-07-10', paymentTerms: 'net7', note: null },
  { id: 'p11', networkId: 'adcombo', networkName: 'AdCombo Demo', vertical: 'sweeps', geo: 'eu', campaignName: 'EU_Sweeps_Pop', buyer: 'Alex M.', amount: 15000, status: 'approved', bookedOn: '2026-07-18', holdUntil: '2026-07-25', daysInHold: null, paidOn: null, paymentTerms: 'net7', note: null },
  { id: 'p12', networkId: 'adcombo', networkName: 'AdCombo Demo', vertical: 'nutra', geo: 'latam', campaignName: 'LATAM_Diet_Push_v2', buyer: 'Mike R.', amount: 20000, status: 'pending', bookedOn: '2026-07-22', holdUntil: '2026-07-29', daysInHold: 1, paidOn: null, paymentTerms: 'net7', note: null },
  { id: 'p13', networkId: 'adcombo', networkName: 'AdCombo Demo', vertical: 'sweeps', geo: 'in', campaignName: 'IN_Sweeps_Broad', buyer: 'Sarah T.', amount: 63000, status: 'scrubbed', bookedOn: '2026-07-10', holdUntil: null, daysInHold: null, paidOn: null, paymentTerms: 'net7', note: 'Massive bot traffic detected by advertiser' },

  // Affise Internal (Overdue hold)
  { id: 'p14', networkId: 'affise_demo', networkName: 'Affise Internal', vertical: 'igaming', geo: 'cis', campaignName: 'CIS_Casino_VK', buyer: 'Elena V.', amount: 30000, status: 'paid', bookedOn: '2026-05-01', holdUntil: '2026-06-01', daysInHold: null, paidOn: '2026-06-05', paymentTerms: 'net30', note: null },
  { id: 'p15', networkId: 'affise_demo', networkName: 'Affise Internal', vertical: 'dating', geo: 'us', campaignName: 'US_Dating_TikTok', buyer: 'David K.', amount: 18400, status: 'pending', bookedOn: '2026-05-20', holdUntil: '2026-06-20', daysInHold: -38, paidOn: null, paymentTerms: 'net30', note: 'Payment delayed due to verification' }, // Overdue!
  { id: 'p16', networkId: 'affise_demo', networkName: 'Affise Internal', vertical: 'igaming', geo: 'cis', campaignName: 'CIS_Casino_TG', buyer: 'Elena V.', amount: 36600, status: 'pending', bookedOn: '2026-07-05', holdUntil: '2026-08-05', daysInHold: 8, paidOn: null, paymentTerms: 'net30', note: null },
  { id: 'p17', networkId: 'affise_demo', networkName: 'Affise Internal', vertical: 'dating', geo: 'uk', campaignName: 'UK_Dating_FB', buyer: 'David K.', amount: 10000, status: 'scrubbed', bookedOn: '2026-06-15', holdUntil: null, daysInHold: null, paidOn: null, paymentTerms: 'net30', note: 'Low retention rate' },

  // CryptoNet X
  { id: 'p18', networkId: 'crypto_net', networkName: 'CryptoNet X', vertical: 'crypto', geo: 'eu', campaignName: 'EU_Trading_Native', buyer: 'Mike R.', amount: 28000, status: 'paid', bookedOn: '2026-06-28', holdUntil: '2026-07-12', daysInHold: null, paidOn: '2026-07-15', paymentTerms: 'weekly', note: null },
  { id: 'p19', networkId: 'crypto_net', networkName: 'CryptoNet X', vertical: 'crypto', geo: 'ca', campaignName: 'CA_Crypto_Search', buyer: 'Alex M.', amount: 5000, status: 'approved', bookedOn: '2026-07-15', holdUntil: '2026-07-22', daysInHold: null, paidOn: null, paymentTerms: 'weekly', note: null },
  { id: 'p20', networkId: 'crypto_net', networkName: 'CryptoNet X', vertical: 'crypto', geo: 'uk', campaignName: 'UK_Crypto_FB', buyer: 'Sarah T.', amount: 10000, status: 'pending', bookedOn: '2026-07-20', holdUntil: '2026-08-03', daysInHold: 6, paidOn: null, paymentTerms: 'weekly', note: null },
  { id: 'p21', networkId: 'crypto_net', networkName: 'CryptoNet X', vertical: 'crypto', geo: 'au', campaignName: 'AU_Trading_Native', buyer: 'Mike R.', amount: 1000, status: 'scrubbed', bookedOn: '2026-07-10', holdUntil: null, daysInHold: null, paidOn: null, paymentTerms: 'weekly', note: 'No deposit' },
  { id: 'p22', networkId: 'crypto_net', networkName: 'CryptoNet X', vertical: 'crypto', geo: 'us', campaignName: 'US_Crypto_Search', buyer: 'Alex M.', amount: 1000, status: 'clawback', bookedOn: '2026-06-01', holdUntil: '2026-06-15', daysInHold: null, paidOn: '2026-06-20', paymentTerms: 'weekly', note: 'Chargeback reported' },
];

export const partnersSummary = {
  totalBooked: networksData.reduce((sum, n) => sum + n.booked, 0),
  totalInHold: networksData.reduce((sum, n) => sum + n.inHold, 0),
  totalApproved: networksData.reduce((sum, n) => sum + n.approved, 0),
  totalPaid: networksData.reduce((sum, n) => sum + n.paid, 0),
  totalScrubbed: networksData.reduce((sum, n) => sum + n.scrubbed, 0),
  totalClawback: networksData.reduce((sum, n) => sum + n.clawback, 0),
  get totalNetConfirmed() { return this.totalPaid + this.totalApproved; },
  get blendedScrubRate() { return (this.totalScrubbed / this.totalBooked) * 100; },
  weightedAvgHoldDays: 28, // Mock average
};
