import axios from 'axios';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// Types
export interface Task {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'paused' | 'cancelled';
  created_at: string;
  started_at?: string;
  completed_at?: string;
  steps: TaskStep[];
  current_step: number;
  error?: string;
  result?: string;
  priority: number;
  logs: string[];
}

export interface TaskStep {
  id: string;
  name: string;
  description: string;
  status: string;
  result?: string;
  error?: string;
  started_at?: string;
  completed_at?: string;
}

export interface Agent {
  name: string;
  status: 'idle' | 'active' | 'error';
  current_action: string;
}

export interface FileInfo {
  name: string;
  path: string;
  size: number;
  modified: string;
  is_dir: boolean;
  extension: string;
}

export interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
  task_id?: string;
  agent?: string;
}

// Task API
export const createTask = async (description: string, title?: string, priority: number = 5): Promise<Task> => {
  const { data } = await api.post('/api/tasks', {
    title: title || description.slice(0, 60),
    description,
    priority,
  });
  return data;
};

export const getTasks = async (): Promise<Task[]> => {
  const { data } = await api.get('/api/tasks');
  return data;
};

export const getTask = async (id: string): Promise<Task> => {
  const { data } = await api.get(`/api/tasks/${id}`);
  return data;
};

export const pauseTask = async (id: string): Promise<void> => {
  await api.post(`/api/tasks/${id}/pause`);
};

export const resumeTask = async (id: string): Promise<void> => {
  await api.post(`/api/tasks/${id}/resume`);
};

export const stopTask = async (id: string): Promise<void> => {
  await api.post(`/api/tasks/${id}/stop`);
};

export const deleteTask = async (id: string): Promise<void> => {
  await api.delete(`/api/tasks/${id}`);
};

export const getTaskLogs = async (id: string): Promise<string[]> => {
  const { data } = await api.get(`/api/tasks/${id}/logs`);
  return data.logs;
};

// Files API
export const getFiles = async (path: string = '.'): Promise<FileInfo[]> => {
  const { data } = await api.get('/api/files', { params: { path } });
  return data;
};

export const getFileContent = async (path: string): Promise<string> => {
  const { data } = await api.get('/api/files/content', { params: { path } });
  return data.content;
};

export const createFile = async (path: string, content: string): Promise<void> => {
  await api.post('/api/files', { path, content });
};

export const deleteFile = async (path: string): Promise<void> => {
  await api.delete('/api/files', { params: { path } });
};

// Agents API
export const getAgents = async (): Promise<Agent[]> => {
  const { data } = await api.get('/api/agents');
  return data;
};

// Logs API
export const getLogs = async (limit: number = 100, level?: string, task_id?: string): Promise<LogEntry[]> => {
  const { data } = await api.get('/api/logs', { params: { limit, level, task_id } });
  return data.logs;
};

// Health check
export const healthCheck = async (): Promise<boolean> => {
  try {
    await api.get('/health');
    return true;
  } catch {
    return false;
  }
};

export default api;
