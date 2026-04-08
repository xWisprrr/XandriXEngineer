import React from 'react';
import { Clock, Trash2, Play } from 'lucide-react';
import type { Task } from '../utils/api';
import { StatusBadge } from './StatusBadge';
import { api } from '../utils/api';

interface TaskHistoryProps {
  tasks: Task[];
  selectedTaskId?: string;
  onSelectTask: (id: string) => void;
  onRefresh: () => void;
}

function timeAgo(date: string): string {
  const seconds = Math.floor((Date.now() - new Date(date).getTime()) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export const TaskHistory: React.FC<TaskHistoryProps> = ({
  tasks, selectedTaskId, onSelectTask, onRefresh,
}) => {
  const handleDelete = async (e: React.MouseEvent, taskId: string) => {
    e.stopPropagation();
    if (!confirm('Delete this task?')) return;
    await api.deleteTask(taskId);
    onRefresh();
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
      <div className="panel-header">
        <span>Task History</span>
        <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>{tasks.length}</span>
      </div>
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {tasks.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '24px 16px', fontSize: 12 }}>
            No tasks yet
          </div>
        ) : (
          tasks.map(task => (
            <div
              key={task.id}
              onClick={() => onSelectTask(task.id)}
              style={{
                padding: '10px 16px',
                cursor: 'pointer',
                borderLeft: `2px solid ${task.id === selectedTaskId ? 'var(--accent)' : 'transparent'}`,
                background: task.id === selectedTaskId ? 'rgba(88,166,255,0.05)' : 'transparent',
                borderBottom: '1px solid var(--border)',
              }}
              onMouseEnter={e => {
                if (task.id !== selectedTaskId)
                  (e.currentTarget as HTMLElement).style.background = 'var(--bg-hover)';
              }}
              onMouseLeave={e => {
                if (task.id !== selectedTaskId)
                  (e.currentTarget as HTMLElement).style.background = 'transparent';
              }}
            >
              <div className="flex items-center justify-between" style={{ marginBottom: 4 }}>
                <StatusBadge status={task.status} />
                <button
                  className="btn btn-ghost btn-sm"
                  style={{ padding: '2px 4px' }}
                  onClick={e => handleDelete(e, task.id)}
                >
                  <Trash2 size={11} />
                </button>
              </div>
              <div
                className="truncate"
                style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)', marginBottom: 2 }}
              >
                {task.title}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-muted)' }}>
                <Clock size={10} />
                <span>{timeAgo(task.created_at)}</span>
                {task.language && (
                  <span style={{ marginLeft: 4, color: 'var(--accent)' }}>
                    {task.language}
                  </span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
