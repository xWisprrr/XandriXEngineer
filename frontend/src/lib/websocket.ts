type MessageHandler = (data: unknown) => void;
type LogHandler = (log: LogMessage) => void;
type TaskUpdateHandler = (task: TaskUpdateMessage) => void;
type AgentActivityHandler = (activity: AgentActivityMessage) => void;

export interface LogMessage {
  level: string;
  message: string;
  timestamp: string;
  task_id?: string;
  agent?: string;
}

export interface TaskUpdateMessage {
  id: string;
  status: string;
  current_step?: number;
  result?: string;
  error?: string;
}

export interface AgentActivityMessage {
  agent: string;
  message: string;
  task_id?: string;
}

export class XandriXWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private clientId: string;
  private reconnectDelay = 2000;
  private maxReconnectDelay = 30000;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private shouldReconnect = true;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  private messageHandlers: MessageHandler[] = [];
  private logHandlers: LogHandler[] = [];
  private taskUpdateHandlers: TaskUpdateHandler[] = [];
  private agentActivityHandlers: AgentActivityHandler[] = [];
  private connectionHandlers: ((connected: boolean) => void)[] = [];

  constructor(url?: string) {
    const wsBase = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
    this.url = url || wsBase;
    this.clientId = `client_${
      typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID().replace(/-/g, '').slice(0, 12)
        : Math.random().toString(36).slice(2, 9)
    }`;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this.shouldReconnect = true;
    this.doConnect();
  }

  private doConnect(): void {
    try {
      this.ws = new WebSocket(`${this.url}/ws/${this.clientId}`);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.reconnectDelay = 2000;
        this.connectionHandlers.forEach(h => h(true));
      };

      this.ws.onmessage = (event: MessageEvent) => {
        try {
          const msg = JSON.parse(event.data);
          this._route(msg);
        } catch (e) {
          console.error('WebSocket parse error:', e);
        }
      };

      this.ws.onclose = () => {
        this.connectionHandlers.forEach(h => h(false));
        if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
          const delay = Math.min(this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts), this.maxReconnectDelay);
          this.reconnectAttempts++;
          this.reconnectTimer = setTimeout(() => this.doConnect(), delay);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    } catch (e) {
      console.error('WebSocket connection failed:', e);
    }
  }

  private _route(msg: Record<string, unknown>): void {
    const type = msg.type as string;
    const data = msg.data;

    this.messageHandlers.forEach(h => h(msg));

    if (type === 'log_message' || type === 'log') {
      this.logHandlers.forEach(h => h(data as LogMessage));
    } else if (
      type === 'task_started' || type === 'task_completed' ||
      type === 'task_failed' || type === 'task_update' ||
      type === 'step_started' || type === 'step_completed'
    ) {
      this.taskUpdateHandlers.forEach(h => h(data as TaskUpdateMessage));
    } else if (type === 'agent_thinking' || type === 'agent_activity') {
      this.agentActivityHandlers.forEach(h => h(data as AgentActivityMessage));
    }
  }

  send(data: unknown): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  disconnect(): void {
    this.shouldReconnect = false;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.push(handler);
    return () => { this.messageHandlers = this.messageHandlers.filter(h => h !== handler); };
  }

  onLog(handler: LogHandler): () => void {
    this.logHandlers.push(handler);
    return () => { this.logHandlers = this.logHandlers.filter(h => h !== handler); };
  }

  onTaskUpdate(handler: TaskUpdateHandler): () => void {
    this.taskUpdateHandlers.push(handler);
    return () => { this.taskUpdateHandlers = this.taskUpdateHandlers.filter(h => h !== handler); };
  }

  onAgentActivity(handler: AgentActivityHandler): () => void {
    this.agentActivityHandlers.push(handler);
    return () => { this.agentActivityHandlers = this.agentActivityHandlers.filter(h => h !== handler); };
  }

  onConnectionChange(handler: (connected: boolean) => void): () => void {
    this.connectionHandlers.push(handler);
    return () => { this.connectionHandlers = this.connectionHandlers.filter(h => h !== handler); };
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

let _wsInstance: XandriXWebSocket | null = null;

export const getWebSocket = (): XandriXWebSocket => {
  if (!_wsInstance) {
    _wsInstance = new XandriXWebSocket();
  }
  return _wsInstance;
};
