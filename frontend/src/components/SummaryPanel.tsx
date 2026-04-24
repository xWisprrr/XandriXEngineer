'use client';
import { useState, useEffect } from 'react';
import { Task, TaskStep } from '@/lib/api';
import {
  CheckCircle,
  XCircle,
  Clock,
  ChevronDown,
  ChevronRight,
  Loader2,
  FileCode2,
  Layers,
} from 'lucide-react';
import clsx from 'clsx';

interface SummaryPanelProps {
  task: Task | null;
}

const STATUS_ICONS: Record<string, React.ReactNode> = {
  completed: <CheckCircle className="w-3.5 h-3.5 text-green-400" />,
  failed: <XCircle className="w-3.5 h-3.5 text-red-400" />,
  running: <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" />,
  pending: <Clock className="w-3.5 h-3.5 text-slate-500" />,
};

const STATUS_COLORS: Record<string, string> = {
  completed: 'text-green-400',
  failed: 'text-red-400',
  running: 'text-indigo-400',
  pending: 'text-slate-500',
  paused: 'text-yellow-400',
  cancelled: 'text-slate-600',
};

function StepRow({ step, index }: { step: TaskStep; index: number }) {
  const [open, setOpen] = useState(false);
  const icon = STATUS_ICONS[step.status] ?? <Clock className="w-3.5 h-3.5 text-slate-500" />;
  const hasDetail = !!(step.result || step.error);

  return (
    <div className="border-b border-[#1e1e2e] last:border-0">
      <button
        onClick={() => hasDetail && setOpen(v => !v)}
        className={clsx(
          'w-full flex items-center gap-2 px-3 py-2 text-xs text-left hover:bg-white/[0.02] transition-colors',
          !hasDetail && 'cursor-default',
        )}
      >
        <span className="text-slate-600 w-5 text-right shrink-0">{index + 1}.</span>
        {icon}
        <span className={clsx('flex-1 truncate', STATUS_COLORS[step.status] ?? 'text-slate-400')}>
          {step.name}
        </span>
        {hasDetail && (
          open
            ? <ChevronDown className="w-3 h-3 text-slate-600 shrink-0" />
            : <ChevronRight className="w-3 h-3 text-slate-600 shrink-0" />
        )}
      </button>

      {open && hasDetail && (
        <div className="px-3 pb-2 ml-10">
          {step.result && (
            <pre className="text-[10px] text-green-300 bg-green-400/5 border border-green-400/10 rounded p-2 whitespace-pre-wrap break-all">
              {step.result}
            </pre>
          )}
          {step.error && (
            <pre className="text-[10px] text-red-300 bg-red-400/5 border border-red-400/10 rounded p-2 whitespace-pre-wrap break-all">
              {step.error}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

function formatDuration(start?: string, end?: string): string {
  if (!start) return '';
  const s = new Date(start).getTime();
  const e = end ? new Date(end).getTime() : Date.now();
  const secs = Math.round((e - s) / 1000);
  if (secs < 60) return `${secs}s`;
  return `${Math.floor(secs / 60)}m ${secs % 60}s`;
}

export default function SummaryPanel({ task }: SummaryPanelProps) {
  const [stepSectionOpen, setStepSectionOpen] = useState(true);

  if (!task) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-6 space-y-3">
        <Layers className="w-8 h-8 text-slate-700" />
        <p className="text-xs text-slate-600">
          Select or start a task to see the execution summary.
        </p>
      </div>
    );
  }

  const statusColor = STATUS_COLORS[task.status] ?? 'text-slate-400';
  const completed = task.steps.filter(s => s.status === 'completed').length;
  const total = task.steps.length;
  const progress = total > 0 ? (completed / total) * 100 : 0;

  const duration = formatDuration(task.started_at, task.completed_at);

  return (
    <div className="flex flex-col h-full overflow-hidden text-xs">
      {/* Header */}
      <div className="px-3 py-2.5 border-b border-[#1e1e2e] space-y-1.5">
        <div className="flex items-start justify-between gap-2">
          <p className="text-slate-200 font-medium leading-tight line-clamp-2">{task.title}</p>
          <span className={clsx('shrink-0 font-medium capitalize', statusColor)}>{task.status}</span>
        </div>

        {/* Progress bar */}
        {total > 0 && (
          <div className="space-y-1">
            <div className="flex justify-between text-slate-600">
              <span>{completed}/{total} steps</span>
              {duration && <span>{duration}</span>}
            </div>
            <div className="h-1 rounded-full bg-[#1e1e2e]">
              <div
                className={clsx(
                  'h-1 rounded-full transition-all duration-500',
                  task.status === 'completed' ? 'bg-green-500' :
                  task.status === 'failed' ? 'bg-red-500' : 'bg-indigo-500',
                )}
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Result / Error */}
      {(task.result || task.error) && (
        <div className={clsx(
          'px-3 py-2 border-b border-[#1e1e2e]',
          task.error ? 'bg-red-500/5' : 'bg-green-500/5',
        )}>
          <p className={clsx('font-medium mb-1', task.error ? 'text-red-400' : 'text-green-400')}>
            {task.error ? 'Error' : 'Result'}
          </p>
          <p className={clsx('leading-relaxed', task.error ? 'text-red-300' : 'text-green-300')}>
            {(task.error || task.result || '').slice(0, 300)}
          </p>
        </div>
      )}

      {/* Steps */}
      {total > 0 && (
        <div className="flex-1 overflow-y-auto">
          <button
            onClick={() => setStepSectionOpen(v => !v)}
            className="w-full flex items-center justify-between px-3 py-2 text-slate-500 hover:text-slate-300 border-b border-[#1e1e2e] transition-colors"
          >
            <span className="font-medium">Execution Steps</span>
            {stepSectionOpen
              ? <ChevronDown className="w-3.5 h-3.5" />
              : <ChevronRight className="w-3.5 h-3.5" />}
          </button>
          {stepSectionOpen && (
            <div>
              {task.steps.map((step, i) => (
                <StepRow key={step.id} step={step} index={i} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Metadata */}
      <div className="px-3 py-2 border-t border-[#1e1e2e] space-y-0.5 text-slate-600 shrink-0">
        <div className="flex justify-between">
          <span>Created</span>
          <span>{new Date(task.created_at).toLocaleTimeString()}</span>
        </div>
        {task.started_at && (
          <div className="flex justify-between">
            <span>Started</span>
            <span>{new Date(task.started_at).toLocaleTimeString()}</span>
          </div>
        )}
        <div className="flex justify-between">
          <span>Priority</span>
          <span>{task.priority}</span>
        </div>
      </div>
    </div>
  );
}
