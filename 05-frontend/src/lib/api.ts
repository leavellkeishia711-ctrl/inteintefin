import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  withCredentials: true, // This allows sending cookies
});

let refreshPromise: Promise<any> | null = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // If the error is 401 and we haven't retried yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      // Prevent infinite loops if refresh itself fails
      if (originalRequest.url === '/api/v1/auth/refresh') {
        return Promise.reject(error);
      }

      try {
        if (!refreshPromise) {
            refreshPromise = api.post('/api/v1/auth/refresh').finally(() => {
                refreshPromise = null;
            });
        }
        
        const { data } = await refreshPromise;
        
        if (data && data.access_token) {
          api.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`;
          originalRequest.headers['Authorization'] = `Bearer ${data.access_token}`;
        }
        
        return api(originalRequest);
      } catch (refreshError) {
        // If refresh fails, redirect to login
        if (typeof window !== 'undefined') {
          const lang = window.location.pathname.startsWith('/ru') ? 'ru' : 'en';
          window.location.href = `/${lang}/login`;
        }
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

export const fetchTransactions = async (params: Record<string, unknown>) => {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value) searchParams.append(key, value.toString());
    });

    const res = await api.get(`/api/v1/transactions?${searchParams.toString()}`);
    return res.data;
};

export const createTransaction = async (data: Record<string, unknown>) => {
    const res = await api.post(`/api/v1/transactions`, data);
    return res.data;
};

export const uploadCsv = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post(`/api/v1/imports/upload`, formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return res.data;
};

export const commitImport = async (batchId: string, columnMapping: Record<string, string>) => {
    const res = await api.post(`/api/v1/imports/${batchId}/commit`, {
        batch_id: batchId,
        column_mapping: columnMapping
    });
    return res.data;
};

export default api;
