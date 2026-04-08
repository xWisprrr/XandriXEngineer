import React, { useEffect, useRef } from 'react';
import { Terminal, Trash2 } from 'lucide-react';
import type { LogEntry } from '../utils/api';

interface ExecutionLogProps {
  logs: LogEntry[];
  onClear: () => void;
  connected: boolean;
}

const levelClass: Record<string, string> = {
  info: 'log-info',
  success: 'log-success',
  warning: 'log-warning',
  error: 'log-error',
  debug: 'log-debug',
};

function getSourceClass(source: string): string {
  if (source.includes('planner')) return 'log-planner';
  if (source.includes('coder')) return 'log-coder';
  if (source.includes('tester')) return 'log-tester';
  if (source.includes('debugger')) return 'log-debugger';
  if (source.includes('devops')) return 'log-devops';
  return '';
}

function formatTime(ts: string): string {
  try {
    return new Date(ts).toLocaleTimeString('en-US', { hour12: false });
  } catch {
    return '';
  }
}

export const ExecutionLog: React.FC<ExecutionLogProps> = ({ logs, onClear, connected }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div className="panel-header">
        <div className="flex items-center gap-2">
          <Terminal size={14} />
          <span>Execution Log</span>
          <span
            style={{
              width: 8, height: 8, borderRadius: '50%',
              background: connected ? 'var(--success)' : 'var(--error)',
              display: 'inline-block',
            }}
          />
        </div>
        <button className="btn btn-ghost btn-sm" onClick={onClear}>
          <Trash2 size={12} /> Clear
        </button>
      </div>

      <div
        className="font-mono"
        style={{
          flex: 1, overflowY: 'auto', padding: '12px 16px',
          fontSize: '12px', lineHeight: '1.6',
          background: 'var(--bg-primary)',
        }}
      >
        {logs.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: 40 }}>
            Waiting for output...
          </div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className={levelClass[log.level] || 'log-info'} style={{ marginBottom: 2 }}>
              <span style={{ color: 'var(--text-muted)', marginRight: 8 }}>
                {formatTime(log.timestamp)}
              </span>
              <span style={{ color: 'var(--text-muted)', marginRight: 8 }}>
                [{log.source}]
              </span>
              <span className={getSourceClass(log.source)}>
                {log.message}
              </span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};
