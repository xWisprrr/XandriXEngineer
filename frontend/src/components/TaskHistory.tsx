'use client';
import { useState, useEffect, useCallback } from 'react';
import { Task, getTasks, deleteTask } from '@/lib/api';
import { Clock, CheckCircle, XCircle, Loader2, PauseCircle, Trash2, RefreshCw } from 'lucide-react';
import clsx from 'clsx';

interface TaskHistoryProps {
  tasks: Task[];
  selectedTask: Task | null;
  onSelectTask: (task: Task) => void;
  onTasksChange: (tasks: Task[]) => void;
}

const STATUS_ICONS: Record<string, React.ReactNode> = {
  pending: <Clock className="w-3 h-3 text-yellow-500" />,
  running: <Loader2 className="w-3 h-3 text-indigo-400 animate-spin" />,
  completed: <CheckCircle className="w-3 h-3 text-green-500" />,
  failed: <XCircle className="w-3 h-3 text-red-500" />,
  paused: <PauseCircle className="w-3 h-3 text-slate-500" />,
  cancelled: <XCircle className="w-3 h-3 text-slate-600" />,
};

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  if (diff < 60000) return 'just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return d.toLocaleDateString();
}

export default function TaskHistory({ tasks, selectedTask, onSelectTask, onTasksChange }: TaskHistoryProps) {
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getTasks();
      onTasksChange(data.reverse());
    } catch (e) {
      console.error('Failed to load tasks:', e);
    } finally {
      setLoading(false);
    }
  }, [onTasksChange]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  const handleDelete = async (e: React.MouseEvent, task: Task) => {
    e.stopPropagation();
    if (!confirm(`Delete task "${task.title}"?`)) return;
    try {
      await deleteTask(task.id);
      onTasksChange(tasks.filter(t => t.id !== task.id));
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };

  const runningCount = tasks.filter(t => t.status === 'running').length;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-[#1e1e2e] shrink-0">
        <span className="text-xs font-medium text-slate-400 flex-1">Tasks</span>
        {runningCount > 0 && (
          <span className="text-xs bg-indigo-500/10 text-indigo-400 px-1.5 py-0.5 rounded-full">
            {runningCount} running
          </span>
        )}
        <button
          onClick={refresh}
          className="p-1 text-slate-600 hover:text-slate-300 transition-colors"
        >
          <RefreshCw className={clsx('w-3 h-3', loading && 'animate-spin')} />
        </button>
      </div>

      {/* Task list */}
      <div className="flex-1 overflow-y-auto">
        {tasks.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-600">
            <Clock className="w-6 h-6 mx-auto mb-2 opacity-30" />
            <p>No tasks yet</p>
          </div>
        ) : (
          tasks.map(task => (
            <div
              key={task.id}
              onClick={() => onSelectTask(task)}
              className={clsx(
                'group flex items-start gap-2 px-3 py-2.5 border-b border-[#1e1e2e]/50 cursor-pointer transition-colors',
                selectedTask?.id === task.id
                  ? 'bg-indigo-500/10 border-l-2 border-l-indigo-500'
                  : 'hover:bg-[#1a1a26]'
              )}
            >
              <div className="shrink-0 mt-0.5">
                {STATUS_ICONS[task.status] || <Clock className="w-3 h-3 text-slate-600" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-slate-200 truncate leading-tight">{task.title}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-xs text-slate-600">{formatDate(task.created_at)}</span>
                  {task.steps.length > 0 && (
                    <span className="text-xs text-slate-600">
                      {task.current_step}/{task.steps.length} steps
                    </span>
                  )}
                </div>
              </div>
              <button
                onClick={e => handleDelete(e, task)}
                className="opacity-0 group-hover:opacity-100 p-0.5 text-slate-600 hover:text-red-400 transition-all shrink-0"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
