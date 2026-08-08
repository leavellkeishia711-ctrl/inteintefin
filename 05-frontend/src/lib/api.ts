import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  withCredentials: true, // This allows sending cookies
});

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
        const { data } = await api.post('/api/v1/auth/refresh');
        
        // Update the access token in headers if needed (though we use bearer, maybe we should attach it)
        if (data.access_token) {
          api.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`;
          originalRequest.headers['Authorization'] = `Bearer ${data.access_token}`;
        }
        
        return api(originalRequest);
      } catch (refreshError) {
        // If refresh fails, redirect to login
        if (typeof window !== 'undefined') {
          // Keep current language if possible, otherwise default to en
          const lang = window.location.pathname.startsWith('/ru') ? 'ru' : 'en';
          window.location.href = `/${lang}/login`;
        }
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

export default api;
