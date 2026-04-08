'use client';
import { useEffect, useRef, useState, useCallback } from 'react';
import { Task, getTaskLogs } from '@/lib/api';
import { getWebSocket } from '@/lib/websocket';
import { Terminal, Trash2, Filter, CheckCircle, XCircle, Info, AlertTriangle, Zap } from 'lucide-react';
import clsx from 'clsx';

interface ExecutionLogsProps {
  task: Task | null;
  extraLogs?: string[];
}

interface LogLine {
  id: string;
  text: string;
  level: 'info' | 'warn' | 'error' | 'debug' | 'step' | 'done';
  timestamp: string;
}

function classifyLog(text: string): LogLine['level'] {
  const t = text.toUpperCase();
  if (t.includes('[ERROR]') || t.includes('ERROR:') || t.includes('FAILED')) return 'error';
  if (t.includes('[WARN]') || t.includes('WARNING:')) return 'warn';
  if (t.includes('[DEBUG]')) return 'debug';
  if (t.includes('[STEP') || t.includes('STEP_')) return 'step';
  if (t.includes('[DONE]') || t.includes('[OK]') || t.includes('COMPLETED')) return 'done';
  return 'info';
}

const LEVEL_STYLES: Record<LogLine['level'], string> = {
  info: 'text-slate-300',
  warn: 'text-yellow-400',
  error: 'text-red-400',
  debug: 'text-blue-400',
  step: 'text-indigo-400',
  done: 'text-green-400',
};

const LEVEL_ICONS: Record<LogLine['level'], React.ReactNode> = {
  info: <Info className="w-3 h-3 shrink-0 mt-0.5" />,
  warn: <AlertTriangle className="w-3 h-3 shrink-0 mt-0.5" />,
  error: <XCircle className="w-3 h-3 shrink-0 mt-0.5" />,
  debug: <Zap className="w-3 h-3 shrink-0 mt-0.5" />,
  step: <Zap className="w-3 h-3 shrink-0 mt-0.5" />,
  done: <CheckCircle className="w-3 h-3 shrink-0 mt-0.5" />,
};

let logIdCounter = 0;

function makeLogLine(text: string): LogLine {
  return {
    id: `log_${++logIdCounter}`,
    text,
    level: classifyLog(text),
    timestamp: new Date().toLocaleTimeString(),
  };
}

export default function ExecutionLogs({ task, extraLogs }: ExecutionLogsProps) {
  const [lines, setLines] = useState<LogLine[]>([]);
  const [filter, setFilter] = useState<LogLine['level'] | 'all'>('all');
  const [autoScroll, setAutoScroll] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Load initial logs for selected task
  useEffect(() => {
    if (!task) return;
    setLines([]);
    getTaskLogs(task.id).then(logs => {
      setLines(logs.map(makeLogLine));
    }).catch(() => {});
  }, [task?.id]);

  // Handle extra logs from WS
  useEffect(() => {
    if (!extraLogs?.length) return;
    const latest = extraLogs[extraLogs.length - 1];
    if (latest) {
      setLines(prev => [...prev.slice(-999), makeLogLine(latest)]);
    }
  }, [extraLogs]);

  // WS subscription
  useEffect(() => {
    const ws = getWebSocket();
    const off = ws.onMessage((msg: unknown) => {
      const m = msg as Record<string, unknown>;
      if (m.type === 'agent_thinking' || m.type === 'step_started' || m.type === 'step_completed') {
        const data = m.data as Record<string, unknown> | undefined;
        if (!task || (data?.task_id && data.task_id !== task.id)) return;
        const text = data?.message as string || JSON.stringify(data);
        setLines(prev => [...prev.slice(-999), makeLogLine(`[${String(m.type).toUpperCase()}] ${text}`)]);
      }
    });
    return off;
  }, [task?.id]);

  // Auto scroll
  useEffect(() => {
    if (autoScroll) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [lines, autoScroll]);

  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
    setAutoScroll(atBottom);
  }, []);

  const clearLogs = () => setLines([]);

  const filteredLines = filter === 'all' ? lines : lines.filter(l => l.level === filter);

  return (
    <div className="flex flex-col h-full bg-[#0d0d15]">
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-3 py-2 border-b border-[#1e1e2e] bg-[#12121a]">
        <Terminal className="w-4 h-4 text-slate-500 shrink-0" />
        <span className="text-xs text-slate-500 font-mono">
          {task ? task.title.slice(0, 40) : 'No task selected'}
        </span>
        <div className="flex-1" />

        <div className="flex items-center gap-1">
          <Filter className="w-3 h-3 text-slate-600" />
          <select
            value={filter}
            onChange={e => setFilter(e.target.value as LogLine['level'] | 'all')}
            className="bg-transparent text-xs text-slate-500 focus:outline-none cursor-pointer"
          >
            <option value="all">All</option>
            <option value="info">Info</option>
            <option value="warn">Warn</option>
            <option value="error">Error</option>
            <option value="debug">Debug</option>
            <option value="step">Steps</option>
            <option value="done">Done</option>
          </select>
        </div>

        <button
          onClick={clearLogs}
          className="p-1 text-slate-600 hover:text-red-400 transition-colors"
          title="Clear logs"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Logs */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-3 py-2 terminal"
      >
        {filteredLines.length === 0 ? (
          <div className="flex items-center justify-center h-full text-slate-600 text-sm">
            <div className="text-center space-y-2">
              <Terminal className="w-8 h-8 mx-auto opacity-30" />
              <p>No logs yet. Start a task to see execution output.</p>
            </div>
          </div>
        ) : (
          <div className="space-y-0.5">
            {filteredLines.map(line => (
              <div key={line.id} className={clsx('flex items-start gap-2 text-xs leading-relaxed', LEVEL_STYLES[line.level])}>
                <span className="text-slate-600 shrink-0 font-mono">{line.timestamp}</span>
                {LEVEL_ICONS[line.level]}
                <span className="break-all">{line.text}</span>
              </div>
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-3 py-1.5 border-t border-[#1e1e2e] bg-[#12121a]">
        <span className="text-xs text-slate-600 font-mono">{filteredLines.length} lines</span>
        {!autoScroll && (
          <button
            onClick={() => { setAutoScroll(true); bottomRef.current?.scrollIntoView(); }}
            className="text-xs text-indigo-400 hover:text-indigo-300"
          >
            ↓ Jump to bottom
          </button>
        )}
      </div>
    </div>
  );
}
