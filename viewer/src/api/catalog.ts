import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Viewer API only reads public /catalog endpoints
export const catalogApi = {
  get: () => api.get('/catalog'),
  search: (params: { q?: string; category?: string; language?: string; section?: string }) => 
    api.get('/catalog/search', { params }),
};
