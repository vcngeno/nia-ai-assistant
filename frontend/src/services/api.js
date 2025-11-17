import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  logout: () => api.post('/auth/logout'),
  getCurrentUser: () => api.get('/auth/me'),
};

// Children API
export const childrenAPI = {
  getAll: () => api.get('/children/'),
  create: (data) => api.post('/children/', data),
  update: (id, data) => api.put(`/children/${id}`, data),
  delete: (id) => api.delete(`/children/${id}`),
  verifyPIN: (data) => api.post('/children/verify-pin', data),
  getStats: (id) => api.get(`/children/${id}/stats`),
};

// Dashboard API
export const dashboardAPI = {
  getOverview: () => api.get('/dashboard/overview'),
  getChildProgress: (childId, days = 30) => 
    api.get(`/dashboard/children/${childId}/progress`, { params: { days } }),
  getConversations: (params) => api.get('/dashboard/conversations', { params }),
  getConversationDetail: (id) => api.get(`/dashboard/conversations/${id}`),
  getAnalytics: (params) => api.get('/dashboard/analytics', { params }),
  exportConversations: (params) => api.get('/dashboard/export/conversations', { params }),
  getSafetyReport: (childId) => api.get(`/dashboard/safety/${childId}`),
  updateSafetySettings: (childId, data) => 
    api.put(`/dashboard/safety/${childId}/settings`, null, { params: data }),
};

// Conversation API
export const conversationAPI = {
  sendMessage: (data) => api.post('/conversation/message', data),
  getConversation: (id) => api.get(`/conversation/conversation/${id}`),
};

export default api;

// Feedback API
export const feedbackAPI = {
  submitFeedback: (messageId, rating) => api.post('/conversation/feedback', { message_id: messageId, rating })
};

// Add to conversationAPI
conversationAPI.submitFeedback = (messageId, rating) => 
  api.post('/conversation/feedback', { message_id: messageId, rating });

// Feedback API
export const feedbackAPI = {
  submitFeedback: (messageId, rating) => api.post('/conversation/feedback', { message_id: messageId, rating })
};

// Add to conversationAPI
conversationAPI.submitFeedback = (messageId, rating) => 
  api.post('/conversation/feedback', { message_id: messageId, rating });
