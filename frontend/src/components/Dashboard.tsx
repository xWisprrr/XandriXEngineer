'use client';
import { useState, useEffect, useCallback } from 'react';
import ChatInterface from './ChatInterface';
import ExecutionLogs from './ExecutionLogs';
import AgentActivity from './AgentActivity';
import FileExplorer from './FileExplorer';
import TaskHistory from './TaskHistory';
import SummaryPanel from './SummaryPanel';
import CodePreview from './CodePreview';
import { Task, getAgents, Agent } from '@/lib/api';
import { getWebSocket } from '@/lib/websocket';
import { Activity, Cpu, Wifi, WifiOff, LayoutList, FileText } from 'lucide-react';

export default function Dashboard() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const [selectedFile, setSelectedFile] = useState<{ path: string; content: string } | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [activeTab, setActiveTab] = useState<'logs' | 'agents'>('logs');
  const [rightTab, setRightTab] = useState<'summary' | 'files'>('summary');
  const [currentProjectId, setCurrentProjectId] = useState<string | null>(null);

  const refreshAgents = useCallback(async () => {
    try {
      const data = await getAgents();
      setAgents(data);
    } catch (e) {
      // Backend might not be up yet
    }
  }, []);

  useEffect(() => {
    refreshAgents();
    const interval = setInterval(refreshAgents, 5000);

    const ws = getWebSocket();
    ws.connect();

    const offConn = ws.onConnectionChange((connected) => {
      setWsConnected(connected);
    });

    const offMsg = ws.onMessage((msg: unknown) => {
      const m = msg as Record<string, unknown>;
      const data = m.data as Record<string, unknown> | undefined;

      if (m.type === 'task_started' || m.type === 'task_completed' || m.type === 'task_failed') {
        if (data) {
          setTasks(prev => {
            const existing = prev.find(t => t.id === (data as Task).id);
            if (existing) {
              return prev.map(t => t.id === (data as Task).id ? { ...t, ...(data as Task) } : t);
            }
            return [...prev, data as Task];
          });
          if (selectedTask?.id === (data as Task).id) {
            setSelectedTask(d => d ? { ...d, ...(data as Task) } : null);
          }
        }
      }

      if (m.type === 'log_message' || m.type === 'step_started' || m.type === 'step_completed' || m.type === 'agent_thinking') {
        const logEntry = data
          ? (typeof data === 'object'
              ? (data as Record<string, unknown>).message as string
                  || (data as Record<string, unknown>).text as string
                  || JSON.stringify(data)
              : String(data))
          : String(m.event);
        setLogs(prev => [...prev.slice(-499), logEntry]);
      }

      if (m.type === 'agent_thinking') {
        refreshAgents();
      }
    });

    return () => {
      clearInterval(interval);
      offConn();
      offMsg();
      ws.disconnect();
    };
  }, [refreshAgents, selectedTask?.id]);

  const handleTaskCreated = (task: Task) => {
    setTasks(prev => {
      const exists = prev.find(t => t.id === task.id);
      if (exists) return prev.map(t => t.id === task.id ? task : t);
      return [task, ...prev];
    });
    setSelectedTask(task);
    setLogs([]);
  };

  const handleTaskSelect = (task: Task) => {
    setSelectedTask(task);
  };

  return (
    <div className="flex flex-col h-screen bg-[#0a0a0f] text-slate-200 overflow-hidden">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-[#1e1e2e] bg-[#12121a] flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center">
            <Cpu className="w-4 h-4 text-indigo-400" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-white">XandriXEngineer</h1>
            <p className="text-xs text-slate-500">Autonomous AI Software Engineer</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-xs">
            {wsConnected ? (
              <><Wifi className="w-3.5 h-3.5 text-green-400" /><span className="text-green-400">Connected</span></>
            ) : (
              <><WifiOff className="w-3.5 h-3.5 text-red-400" /><span className="text-red-400">Disconnected</span></>
            )}
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Activity className="w-3.5 h-3.5" />
            <span>{tasks.filter(t => t.status === 'running').length} running</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar */}
        <aside className="w-64 border-r border-[#1e1e2e] flex flex-col overflow-hidden bg-[#12121a] flex-shrink-0">
          <TaskHistory
            tasks={tasks}
            selectedTask={selectedTask}
            onSelectTask={handleTaskSelect}
            onTasksChange={setTasks}
          />
        </aside>

        {/* Main Area — Chat + Logs */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Chat Interface */}
          <div className="flex-1 overflow-hidden border-b border-[#1e1e2e]">
            <ChatInterface
              onTaskCreated={handleTaskCreated}
              currentProjectId={currentProjectId}
              onProjectCreated={setCurrentProjectId}
            />
          </div>

          {/* Execution Logs / Agent Activity tabs */}
          <div className="h-56 flex flex-col overflow-hidden">
            <div className="flex border-b border-[#1e1e2e] bg-[#12121a] shrink-0">
              <button
                onClick={() => setActiveTab('logs')}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === 'logs'
                    ? 'text-indigo-400 border-b-2 border-indigo-400'
                    : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                Execution Logs
              </button>
              <button
                onClick={() => setActiveTab('agents')}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === 'agents'
                    ? 'text-indigo-400 border-b-2 border-indigo-400'
                    : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                Agent Activity
              </button>
            </div>
            <div className="flex-1 overflow-hidden">
              {activeTab === 'logs' ? (
                <ExecutionLogs task={selectedTask} extraLogs={logs} />
              ) : (
                <AgentActivity agents={agents} />
              )}
            </div>
          </div>
        </main>

        {/* Right Sidebar — Summary + File Explorer */}
        <aside className="w-72 border-l border-[#1e1e2e] flex flex-col overflow-hidden bg-[#12121a] flex-shrink-0">
          {/* Tab bar */}
          <div className="flex border-b border-[#1e1e2e] shrink-0">
            <button
              onClick={() => setRightTab('summary')}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-medium transition-colors ${
                rightTab === 'summary'
                  ? 'text-indigo-400 border-b-2 border-indigo-400'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              <LayoutList className="w-3.5 h-3.5" />
              Summary
            </button>
            <button
              onClick={() => setRightTab('files')}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-medium transition-colors ${
                rightTab === 'files'
                  ? 'text-indigo-400 border-b-2 border-indigo-400'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              Files
            </button>
          </div>

          {/* Panel content */}
          <div className="flex-1 overflow-hidden">
            {rightTab === 'summary' ? (
              <SummaryPanel task={selectedTask} />
            ) : (
              <>
                <FileExplorer onFileSelect={setSelectedFile} />
                {selectedFile && (
                  <div className="border-t border-[#1e1e2e] overflow-hidden" style={{ maxHeight: '50%' }}>
                    <CodePreview path={selectedFile.path} content={selectedFile.content} />
                  </div>
                )}
              </>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
