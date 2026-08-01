import { useQuery } from '@tanstack/react-query';
import { api, unwrap } from './api-client';

export const usePnL = (params: { start_date: string; end_date: string; team_id?: string; user_id?: string }) => {
  return useQuery({
    queryKey: ['pnl', params],
    queryFn: () => unwrap(api.GET('/api/v1/reports/pnl', { params: { query: params as any } })),
  });
};

export const useCashFlow = (params: { start_date: string; end_date: string; team_id?: string }) => {
  return useQuery({
    queryKey: ['cashFlow', params],
    queryFn: () => unwrap(api.GET('/api/v1/reports/cash-flow', { params: { query: params as any } })),
  });
};

export const useHealth = (params: { start_date: string; end_date: string; team_id?: string }) => {
  return useQuery({
    queryKey: ['health', params],
    queryFn: () => unwrap(api.GET('/api/v1/reports/health', { params: { query: params as any } })),
  });
};

export const useTransactions = (params?: { page?: number; per_page?: number; search?: string }) => {
  return useQuery({
    queryKey: ['transactions', params],
    queryFn: () => unwrap(api.GET('/api/v1/transactions/', { params: { query: params } })),
  });
};

export const useCampaignRuns = (params?: { skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['campaignRuns', params],
    queryFn: () => unwrap(api.GET('/api/v1/campaign-runs/', { params: { query: params as any } })),
  });
};

export const usePayroll = () => {
  return useQuery({
    queryKey: ['payroll'],
    queryFn: async () => {
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + '/api/v1/payroll');
      if (!res.ok) throw new Error('Network error');
      return res.json();
    }
  });
};

export const usePartners = () => {
  return useQuery({
    queryKey: ['partners'],
    queryFn: async () => {
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + '/api/v1/partners');
      if (!res.ok) throw new Error('Network error');
      return res.json();
    }
  });
};




