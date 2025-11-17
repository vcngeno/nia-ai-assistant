import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth API
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
};

// Children API
export const childrenAPI = {
  getAll: () => api.get('/children/'),
  create: (data) => api.post('/children/', data),
  verifyPin: (childId, pin) => api.post('/children/verify-pin', { child_id: childId, pin }),
};

// Conversation API
export const conversationAPI = {
  sendMessage: (data) => api.post('/conversation/message', data),
  getConversation: (conversationId) => api.get(`/conversation/${conversationId}`),
  submitFeedback: (messageId, rating) => api.post('/conversation/feedback', { message_id: messageId, rating }),
};

// Dashboard API
export const dashboardAPI = {
  getOverview: () => api.get('/dashboard/overview'),
  getRecentActivity: () => api.get('/dashboard/recent-activity'),
};

export default api;
