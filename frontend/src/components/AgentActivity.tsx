'use client';
import { Agent } from '@/lib/api';
import clsx from 'clsx';
import { Bot, Code, Bug, Eye, TestTube, Workflow } from 'lucide-react';

interface AgentActivityProps {
  agents: Agent[];
}

const AGENT_ICONS: Record<string, React.ReactNode> = {
  planner: <Workflow className="w-4 h-4" />,
  coder: <Code className="w-4 h-4" />,
  tester: <TestTube className="w-4 h-4" />,
  debugger: <Bug className="w-4 h-4" />,
  reviewer: <Eye className="w-4 h-4" />,
};

const AGENT_COLORS: Record<string, string> = {
  planner: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
  coder: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
  tester: 'text-green-400 bg-green-500/10 border-green-500/20',
  debugger: 'text-red-400 bg-red-500/10 border-red-500/20',
  reviewer: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
};

const DEFAULT_AGENTS = ['planner', 'coder', 'tester', 'debugger', 'reviewer'];

export default function AgentActivity({ agents }: AgentActivityProps) {
  // Merge with defaults so all agents always show
  const agentMap = new Map(agents.map(a => [a.name, a]));
  const displayAgents = DEFAULT_AGENTS.map(name =>
    agentMap.get(name) || { name, status: 'idle' as const, current_action: '' }
  );

  return (
    <div className="h-full overflow-y-auto p-4">
      <div className="space-y-3">
        {displayAgents.map(agent => {
          const isActive = agent.status === 'active';
          const isError = agent.status === 'error';
          const colorClass = AGENT_COLORS[agent.name] || 'text-slate-400 bg-slate-500/10 border-slate-500/20';

          return (
            <div
              key={agent.name}
              className={clsx(
                'rounded-lg border p-3 transition-all',
                isActive ? colorClass : 'bg-[#1a1a26] border-[#2a2a40]',
                isActive && 'shadow-lg'
              )}
            >
              <div className="flex items-center gap-3">
                {/* Status indicator */}
                <div className="relative shrink-0">
                  <div
                    className={clsx(
                      'w-8 h-8 rounded-lg flex items-center justify-center',
                      isActive ? colorClass : 'bg-[#22223a] text-slate-500',
                      isError && 'bg-red-500/10 text-red-400'
                    )}
                  >
                    {AGENT_ICONS[agent.name] || <Bot className="w-4 h-4" />}
                  </div>
                  {isActive && (
                    <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-green-400 rounded-full border-2 border-[#12121a] animate-pulse" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium capitalize text-slate-200">{agent.name}</span>
                    <span
                      className={clsx(
                        'text-xs px-1.5 py-0.5 rounded-full',
                        isActive && 'bg-green-500/10 text-green-400',
                        isError && 'bg-red-500/10 text-red-400',
                        !isActive && !isError && 'bg-slate-500/10 text-slate-500'
                      )}
                    >
                      {agent.status}
                    </span>
                  </div>
                  {agent.current_action ? (
                    <p className="text-xs text-slate-400 truncate mt-0.5">{agent.current_action}</p>
                  ) : (
                    <p className="text-xs text-slate-600 mt-0.5">Idle — waiting for task</p>
                  )}
                </div>

                {/* Progress indicator for active agents */}
                {isActive && (
                  <div className="shrink-0">
                    <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin opacity-60" />
                  </div>
                )}
              </div>

              {/* Action progress bar */}
              {isActive && (
                <div className="mt-2 h-0.5 bg-current/10 rounded-full overflow-hidden">
                  <div className="h-full bg-current/40 rounded-full animate-pulse" style={{ width: '60%' }} />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {agents.length === 0 && (
        <div className="text-center py-8 text-slate-600 text-sm">
          <Bot className="w-8 h-8 mx-auto mb-2 opacity-30" />
          <p>Agents idle — start a task to see activity</p>
        </div>
      )}
    </div>
  );
}
