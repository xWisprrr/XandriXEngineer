import { useEffect, useRef, useState, useCallback } from 'react';
import { createWebSocket, type LogEntry, type Task, type WSMessage } from '../utils/api';

export function useWebSocket(taskId?: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [connected, setConnected] = useState(false);

  const handleMessage = useCallback((msg: WSMessage) => {
    if (msg.type === 'log') {
      setLogs(prev => [...prev.slice(-500), msg.data]);
    }
  }, []);

  useEffect(() => {
    const ws = createWebSocket(handleMessage, taskId);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);

    return () => {
      ws.close();
    };
  }, [taskId, handleMessage]);

  const clearLogs = useCallback(() => setLogs([]), []);

  return { logs, connected, clearLogs };
}

export function useTaskWebSocket(
  taskId: string,
  onTaskUpdate: (task: Task) => void,
  onEvent: (event: string, data: Record<string, unknown>) => void
) {
  const wsRef = useRef<WebSocket | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!taskId) return;

    const ws = createWebSocket((msg: WSMessage) => {
      if (msg.type === 'log') {
        setLogs(prev => [...prev.slice(-1000), msg.data]);
      } else if (msg.type === 'task_state') {
        onTaskUpdate(msg.data);
      } else if (msg.type === 'task_event') {
        onEvent(msg.event, msg.data);
      }
    }, taskId);

    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);

    return () => ws.close();
  }, [taskId]);

  return { logs, connected };
}
