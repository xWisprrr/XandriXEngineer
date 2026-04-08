// XandriX Engineer - API Client & Types

export const API_BASE = '/api';
export const WS_BASE = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}`;

// ─── Types ────────────────────────────────────────────────────────────────────

export type TaskStatus =
  | 'pending' | 'planning' | 'running' | 'paused'
  | 'completed' | 'failed' | 'cancelled';

export type AgentType = 'planner' | 'coder' | 'tester' | 'debugger' | 'devops' | 'reviewer';

export interface TaskStep {
  id: string;
  title: string;
  description: string;
  agent: AgentType;
  status: TaskStatus;
  output?: string;
  error?: string;
  started_at?: string;
  completed_at?: string;
}

export interface Task {
  id: string;
  title: string;
  description: string;
  status: TaskStatus;
  steps: TaskStep[];
  current_step: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  project_dir?: string;
  language?: string;
  context: Record<string, unknown>;
  iterations: number;
  error_count: number;
}

export interface LogEntry {
  id: string;
  task_id?: string;
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'debug' | 'success';
  source: string;
  message: string;
  data?: unknown;
}

export interface FileNode {
  name: string;
  path: string;
  is_dir: boolean;
  size?: number;
  modified?: string;
  children?: FileNode[];
  language?: string;
}

export interface SystemInfo {
  llm_provider: string;
  llm_model: string;
  supported_languages: string[];
  running_tasks: string[];
}

// ─── API Functions ─────────────────────────────────────────────────────────

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(API_BASE + url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API error ${res.status}: ${err}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  // Tasks
  createTask: (title: string, description: string, language?: string) =>
    fetchJSON<Task>('/tasks', {
      method: 'POST',
      body: JSON.stringify({ title, description, language }),
    }),

  listTasks: () => fetchJSON<Task[]>('/tasks'),

  getTask: (id: string) => fetchJSON<Task>(`/tasks/${id}`),

  deleteTask: (id: string) =>
    fetchJSON<{ message: string }>(`/tasks/${id}`, { method: 'DELETE' }),

  controlTask: (id: string, action: string) =>
    fetchJSON<{ message: string }>(`/tasks/${id}/control`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    }),

  // Files
  getTaskFiles: (id: string) => fetchJSON<FileNode>(`/tasks/${id}/files`),

  getFileContent: (id: string, path: string) =>
    fetchJSON<{ path: string; content: string; language?: string }>(
      `/tasks/${id}/files/content?path=${encodeURIComponent(path)}`
    ),

  // System
  getSystemInfo: () => fetchJSON<SystemInfo>('/system/info'),

  health: () => fetchJSON<{ status: string }>('/health'),

  // Chat
  chat: (content: string, taskId?: string) =>
    fetchJSON<{ response: string }>('/chat', {
      method: 'POST',
      body: JSON.stringify({ role: 'user', content, task_id: taskId }),
    }),
};

// ─── WebSocket ──────────────────────────────────────────────────────────────

export type WSMessage =
  | { type: 'log'; data: LogEntry }
  | { type: 'task_event'; event: string; task_id: string; data: Record<string, unknown> }
  | { type: 'task_state'; data: Task };

export function createWebSocket(
  onMessage: (msg: WSMessage) => void,
  taskId?: string
): WebSocket {
  const url = taskId ? `${WS_BASE}/ws/${taskId}` : `${WS_BASE}/ws`;
  const ws = new WebSocket(url);

  ws.onopen = () => {
    const ping = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send('ping');
      else clearInterval(ping);
    }, 30000);
  };

  ws.onmessage = (e) => {
    try {
      if (e.data === 'pong') return;
      const msg = JSON.parse(e.data) as WSMessage;
      onMessage(msg);
    } catch {
      // ignore parse errors
    }
  };

  return ws;
}
