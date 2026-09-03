import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 — redirect to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;

// --- Auth ---
export const authApi = {
  login: (username: string, password: string) =>
    api.post('/auth/login', { username, password }),
  me: () => api.get('/auth/me'),
};

// --- Shows ---
export const showsApi = {
  list: (params: Record<string, string | number>) =>
    api.get('/admin/shows', { params }),
  get: (id: string) => api.get(`/admin/shows/${id}`),
  create: (data: Record<string, unknown>) => api.post('/admin/shows', data),
  update: (id: string, data: Record<string, unknown>) =>
    api.patch(`/admin/shows/${id}`, data),
  delete: (id: string) => api.delete(`/admin/shows/${id}`),
};

// --- Episodes ---
export const episodesApi = {
  list: (params: Record<string, string | number>) =>
    api.get('/admin/episodes', { params }),
  get: (id: string) => api.get(`/admin/episodes/${id}`),
  create: (data: Record<string, unknown>) => api.post('/admin/episodes', data),
  update: (id: string, data: Record<string, unknown>) =>
    api.patch(`/admin/episodes/${id}`, data),
  delete: (id: string) => api.delete(`/admin/episodes/${id}`),
};

// --- Artwork ---
export const artworkApi = {
  upload: (showId: string, type: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/admin/shows/${showId}/artwork/${type}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// --- Publish ---
export const publishApi = {
  validationReport: () => api.get('/admin/validation-report'),
  publish: () => api.post('/admin/catalog/publish'),
  history: (limit = 20) => api.get('/admin/publish-history', { params: { limit } }),
};
