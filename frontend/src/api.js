import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

// ─── TASKS ───

export const fetchTasks = () => api.get('/tasks').then(r => r.data);

export const createTask = (task) => api.post('/tasks', task).then(r => r.data);

export const updateTask = (id, data) => api.patch(`/tasks/${id}`, data).then(r => r.data);

export const deleteTask = (id) => api.delete(`/tasks/${id}`).then(r => r.data);

export const clearCompleted = () => api.delete('/tasks/clear/completed').then(r => r.data);

export const clearAllTasks = () => api.delete('/tasks/clear/all').then(r => r.data);

export const getSummary = () => api.get('/tasks/summary').then(r => r.data);

export const exportTasks = (fmt) => api.get(`/tasks/export/${fmt}`).then(r => r.data);

// ─── CHAT ───

export const sendChat = (message, history) =>
  api.post('/chat', { message, history }).then(r => r.data);

export const getChatHistory = () => api.get('/chat/history').then(r => r.data);

export const clearChatHistory = () => api.delete('/chat/history').then(r => r.data);

// ─── OLLAMA STATUS ───

export const getOllamaStatus = () => api.get('/ollama-status').then(r => r.data);

export default api;
