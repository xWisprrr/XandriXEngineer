'use client';
import { useState } from 'react';
import { createTask, pauseTask, resumeTask, stopTask, Task } from '@/lib/api';
import { Play, Pause, Square, Send, Loader2, ChevronDown } from 'lucide-react';
import clsx from 'clsx';

interface TaskInputProps {
  onTaskCreated: (task: Task) => void;
  currentTask: Task | null;
}

const PRIORITY_OPTIONS = [
  { value: 1, label: 'Low' },
  { value: 5, label: 'Normal' },
  { value: 8, label: 'High' },
  { value: 10, label: 'Critical' },
];

const PROVIDER_OPTIONS = [
  { value: 'openai', label: 'OpenAI GPT-4o' },
  { value: 'anthropic', label: 'Anthropic Claude' },
  { value: 'local', label: 'Local (Rule-based)' },
];

export default function TaskInput({ onTaskCreated, currentTask }: TaskInputProps) {
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState(5);
  const [provider, setProvider] = useState('openai');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const task = await createTask(description.trim(), undefined, priority);
      onTaskCreated(task);
      setDescription('');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create task';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handlePause = async () => {
    if (!currentTask) return;
    try { await pauseTask(currentTask.id); } catch (e) { console.error(e); }
  };

  const handleResume = async () => {
    if (!currentTask) return;
    try { await resumeTask(currentTask.id); } catch (e) { console.error(e); }
  };

  const handleStop = async () => {
    if (!currentTask) return;
    try { await stopTask(currentTask.id); } catch (e) { console.error(e); }
  };

  const taskStatus = currentTask?.status;
  const isRunning = taskStatus === 'running';
  const isPaused = taskStatus === 'paused';

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {/* Description input */}
      <div className="relative">
        <textarea
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder="Describe what you want to build, fix, or automate..."
          rows={3}
          className="w-full bg-[#1a1a26] border border-[#2a2a40] rounded-lg px-4 py-3 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 resize-none transition-all"
          onKeyDown={e => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
              handleSubmit(e);
            }
          }}
        />
      </div>

      {/* Controls row */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Provider selector */}
        <div className="relative">
          <select
            value={provider}
            onChange={e => setProvider(e.target.value)}
            className="appearance-none bg-[#1a1a26] border border-[#2a2a40] rounded-md pl-3 pr-8 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500/50 cursor-pointer"
          >
            {PROVIDER_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-500 pointer-events-none" />
        </div>

        {/* Priority selector */}
        <div className="relative">
          <select
            value={priority}
            onChange={e => setPriority(Number(e.target.value))}
            className="appearance-none bg-[#1a1a26] border border-[#2a2a40] rounded-md pl-3 pr-8 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500/50 cursor-pointer"
          >
            {PRIORITY_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label} Priority</option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-500 pointer-events-none" />
        </div>

        <div className="flex-1" />

        {/* Task controls */}
        {currentTask && (isRunning || isPaused) && (
          <div className="flex items-center gap-2">
            {isRunning ? (
              <button type="button" onClick={handlePause} className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 text-xs hover:bg-yellow-500/20 transition-colors">
                <Pause className="w-3 h-3" />
                Pause
              </button>
            ) : (
              <button type="button" onClick={handleResume} className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-green-500/10 border border-green-500/20 text-green-400 text-xs hover:bg-green-500/20 transition-colors">
                <Play className="w-3 h-3" />
                Resume
              </button>
            )}
            <button type="button" onClick={handleStop} className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-red-500/10 border border-red-500/20 text-red-400 text-xs hover:bg-red-500/20 transition-colors">
              <Square className="w-3 h-3" />
              Stop
            </button>
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !description.trim()}
          className={clsx(
            'flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-all',
            loading || !description.trim()
              ? 'bg-indigo-500/20 text-indigo-400/50 cursor-not-allowed'
              : 'bg-indigo-500 hover:bg-indigo-600 text-white shadow-lg shadow-indigo-500/20'
          )}
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
          {loading ? 'Starting...' : 'Run Task'}
        </button>
      </div>

      {error && (
        <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-md px-3 py-2">
          {error}
        </p>
      )}

      {currentTask && (
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span>Current:</span>
          <span className="text-slate-300 truncate max-w-xs">{currentTask.title}</span>
          <span className={clsx('badge', `badge-${currentTask.status}`)}>
            {currentTask.status}
          </span>
        </div>
      )}
    </form>
  );
}
