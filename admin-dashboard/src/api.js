import axios from 'axios';

export const api = axios.create({
  baseURL: `${(import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')}/admin-api`,
  timeout: 15000,
});

api.interceptors.request.use((request) => {
  const token = localStorage.getItem('admin_token');
  if (token) request.headers.Authorization = `Bearer ${token}`;
  return request;
});
