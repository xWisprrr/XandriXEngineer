import React from 'react';
import { CheckCircle, Circle, Clock, AlertCircle, Loader } from 'lucide-react';
import type { Task } from '../utils/api';

interface AgentActivityProps {
  task: Task | null;
}

const agentColors: Record<string, string> = {
  planner: 'var(--purple)',
  coder: 'var(--accent)',
  tester: 'var(--success)',
  debugger: 'var(--error)',
  devops: 'var(--orange)',
  reviewer: 'var(--warning)',
};

const agentEmoji: Record<string, string> = {
  planner: '🗺️',
  coder: '💻',
  tester: '🧪',
  debugger: '🔍',
  devops: '⚙️',
  reviewer: '👁️',
};

function StepIcon({ status }: { status: string }) {
  switch (status) {
    case 'completed': return <CheckCircle size={14} color="var(--success)" />;
    case 'failed': return <AlertCircle size={14} color="var(--error)" />;
    case 'running': return <Loader size={14} color="var(--accent)" style={{ animation: 'spin 1s linear infinite' }} />;
    default: return <Circle size={14} color="var(--text-muted)" />;
  }
}

export const AgentActivity: React.FC<AgentActivityProps> = ({ task }) => {
  if (!task) {
    return (
      <div style={{ padding: 24, color: 'var(--text-muted)', textAlign: 'center' }}>
        No active task
      </div>
    );
  }

  const totalSteps = task.steps.length;
  const completedSteps = task.steps.filter(s => s.status === 'completed').length;
  const progress = totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div className="panel-header">
        <span>Agent Activity</span>
        <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>
          {completedSteps}/{totalSteps} steps
        </span>
      </div>

      {/* Progress bar */}
      <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--border)' }}>
        <div style={{
          height: 4, background: 'var(--bg-tertiary)', borderRadius: 2, overflow: 'hidden'
        }}>
          <div style={{
            height: '100%', width: `${progress}%`,
            background: 'var(--accent)', borderRadius: 2,
            transition: 'width 0.5s ease',
          }} />
        </div>
        <div style={{ marginTop: 4, fontSize: 11, color: 'var(--text-muted)' }}>
          {task.language && <span style={{ marginRight: 8 }}>🌐 {task.language}</span>}
          <span>Iter: {task.iterations}</span>
          {task.error_count > 0 && (
            <span style={{ marginLeft: 8, color: 'var(--warning)' }}>
              ⚠️ {task.error_count} errors
            </span>
          )}
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
        {task.steps.map((step, idx) => {
          const isActive = idx === task.current_step && task.status === 'running';
          const color = agentColors[step.agent] || 'var(--text-secondary)';
          const emoji = agentEmoji[step.agent] || '🤖';

          return (
            <div
              key={step.id}
              style={{
                padding: '8px 16px',
                borderLeft: `2px solid ${isActive ? color : 'transparent'}`,
                background: isActive ? 'rgba(88,166,255,0.05)' : 'transparent',
                marginBottom: 2,
              }}
            >
              <div className="flex items-center gap-2" style={{ marginBottom: 2 }}>
                <StepIcon status={step.status} />
                <span style={{ fontSize: 11, color, fontWeight: 500 }}>
                  {emoji} {step.agent.toUpperCase()}
                </span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>
                  {idx + 1}
                </span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-primary)', paddingLeft: 22 }}>
                {step.title}
              </div>
              {step.error && (
                <div style={{
                  fontSize: 11, color: 'var(--error)', paddingLeft: 22, marginTop: 2,
                  wordBreak: 'break-word',
                }}>
                  ↳ {step.error.slice(0, 120)}
                </div>
              )}
              {isActive && (
                <div style={{
                  fontSize: 11, color: color, paddingLeft: 22, marginTop: 2,
                  animation: 'pulse 1.5s infinite',
                }}>
                  ● Working...
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
