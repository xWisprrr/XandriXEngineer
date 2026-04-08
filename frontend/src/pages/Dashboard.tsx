import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Play, Square, Pause, RotateCcw, RefreshCw,
  Layout, Code2, MessageSquare, FolderOpen, Activity,
} from 'lucide-react';
import { api, type FileNode, type Task } from '../utils/api';
import { TaskInput } from '../components/TaskInput';
import { TaskHistory } from '../components/TaskHistory';
import { ExecutionLog } from '../components/ExecutionLog';
import { AgentActivity } from '../components/AgentActivity';
import { FileExplorer } from '../components/FileExplorer';
import { ChatPanel } from '../components/ChatPanel';
import { StatusBadge } from '../components/StatusBadge';
import { useWebSocket } from '../hooks/useWebSocket';

type RightPanel = 'activity' | 'files' | 'chat' | 'code';

export const Dashboard: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [fileTree, setFileTree] = useState<FileNode | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | undefined>();
  const [fileContent, setFileContent] = useState<{ content: string; language?: string } | null>(null);
  const [rightPanel, setRightPanel] = useState<RightPanel>('activity');
  const { logs, connected, clearLogs } = useWebSocket();

  const loadTasks = useCallback(async () => {
    try {
      const data = await api.listTasks();
      setTasks(data);
    } catch (e) {
      console.error('Failed to load tasks', e);
    }
  }, []);

  const loadTask = useCallback(async (id: string) => {
    try {
      const task = await api.getTask(id);
      setSelectedTask(task);
    } catch (e) {
      console.error('Failed to load task', e);
    }
  }, []);

  const loadFiles = useCallback(async (id: string) => {
    try {
      const tree = await api.getTaskFiles(id);
      setFileTree(tree);
    } catch {
      setFileTree(null);
    }
  }, []);

  useEffect(() => {
    loadTasks();
    const interval = setInterval(loadTasks, 5000);
    return () => clearInterval(interval);
  }, [loadTasks]);

  useEffect(() => {
    if (!selectedTaskId) return;
    loadTask(selectedTaskId);
    loadFiles(selectedTaskId);
    const interval = setInterval(() => {
      loadTask(selectedTaskId);
      if (rightPanel === 'files') loadFiles(selectedTaskId);
    }, 3000);
    return () => clearInterval(interval);
  }, [selectedTaskId, rightPanel, loadTask, loadFiles]);

  const handleTaskCreated = (taskId: string) => {
    setSelectedTaskId(taskId);
    loadTasks();
    clearLogs();
  };

  const handleSelectTask = (id: string) => {
    setSelectedTaskId(id);
    setSelectedFile(undefined);
    setFileContent(null);
  };

  const handleFileSelect = async (path: string) => {
    if (!selectedTaskId) return;
    setSelectedFile(path);
    setRightPanel('code');
    try {
      const data = await api.getFileContent(selectedTaskId, path);
      setFileContent(data);
    } catch {
      setFileContent(null);
    }
  };

  const handleControl = async (action: string) => {
    if (!selectedTaskId) return;
    try {
      await api.controlTask(selectedTaskId, action);
      setTimeout(() => loadTask(selectedTaskId), 500);
    } catch (e) {
      console.error('Control failed', e);
    }
  };

  return (
    <div className="app">
      {/* Sidebar */}
      <div className="sidebar">
        {/* Logo */}
        <div style={{
          padding: '16px', borderBottom: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: 'linear-gradient(135deg, var(--accent), var(--purple))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontWeight: 800, fontSize: 14, color: 'white',
          }}>X</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14 }}>XandriX</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Engineer v1.0</div>
          </div>
          <div style={{ marginLeft: 'auto' }}>
            <span style={{
              width: 8, height: 8, borderRadius: '50%',
              background: connected ? 'var(--success)' : 'var(--error)',
              display: 'inline-block',
            }} title={connected ? 'Connected' : 'Disconnected'} />
          </div>
        </div>

        <TaskInput onTaskCreated={handleTaskCreated} />

        <TaskHistory
          tasks={tasks}
          selectedTaskId={selectedTaskId || undefined}
          onSelectTask={handleSelectTask}
          onRefresh={loadTasks}
        />
      </div>

      {/* Main Content */}
      <div className="main-content">
        {/* Task Header */}
        {selectedTask ? (
          <div style={{
            padding: '12px 20px', borderBottom: '1px solid var(--border)',
            display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0,
            background: 'var(--bg-secondary)',
          }}>
            <StatusBadge status={selectedTask.status} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="truncate" style={{ fontWeight: 600, fontSize: 15 }}>
                {selectedTask.title}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                Step {selectedTask.current_step}/{selectedTask.steps.length}
                {selectedTask.language && ` · ${selectedTask.language}`}
                {selectedTask.iterations > 0 && ` · ${selectedTask.iterations} iterations`}
              </div>
            </div>
            {/* Controls */}
            <div style={{ display: 'flex', gap: 6 }}>
              {selectedTask.status === 'running' && (
                <>
                  <button className="btn btn-ghost btn-sm" onClick={() => handleControl('pause')}>
                    <Pause size={13} /> Pause
                  </button>
                  <button className="btn btn-danger btn-sm" onClick={() => handleControl('stop')}>
                    <Square size={13} /> Stop
                  </button>
                </>
              )}
              {selectedTask.status === 'paused' && (
                <button className="btn btn-primary btn-sm" onClick={() => handleControl('resume')}>
                  <Play size={13} /> Resume
                </button>
              )}
              {(selectedTask.status === 'failed' || selectedTask.status === 'cancelled') && (
                <button className="btn btn-ghost btn-sm" onClick={() => handleControl('retry')}>
                  <RotateCcw size={13} /> Retry
                </button>
              )}
              <button className="btn btn-ghost btn-sm" onClick={() => loadTask(selectedTask.id)}>
                <RefreshCw size={13} />
              </button>
            </div>
          </div>
        ) : (
          <div style={{
            padding: '12px 20px', borderBottom: '1px solid var(--border)',
            background: 'var(--bg-secondary)', color: 'var(--text-muted)',
            fontSize: 14,
          }}>
            Select or create a task to get started
          </div>
        )}

        {/* Split View */}
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
          {/* Left: Execution Log */}
          <div style={{
            flex: 1, minWidth: 0,
            borderRight: '1px solid var(--border)',
            display: 'flex', flexDirection: 'column',
            overflow: 'hidden',
          }}>
            <ExecutionLog logs={logs} onClear={clearLogs} connected={connected} />
          </div>

          {/* Right: Panels */}
          <div style={{ width: 360, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Tab Bar */}
            <div style={{
              display: 'flex', borderBottom: '1px solid var(--border)',
              background: 'var(--bg-secondary)',
            }}>
              {([
                { id: 'activity', icon: Activity, label: 'Activity' },
                { id: 'files', icon: FolderOpen, label: 'Files' },
                { id: 'code', icon: Code2, label: 'Code' },
                { id: 'chat', icon: MessageSquare, label: 'Chat' },
              ] as const).map(tab => (
                <button
                  key={tab.id}
                  onClick={() => {
                    setRightPanel(tab.id);
                    if (tab.id === 'files' && selectedTaskId) loadFiles(selectedTaskId);
                  }}
                  style={{
                    flex: 1, padding: '10px 4px', fontSize: 11, fontWeight: 500,
                    background: 'transparent',
                    color: rightPanel === tab.id ? 'var(--accent)' : 'var(--text-muted)',
                    borderBottom: rightPanel === tab.id ? '2px solid var(--accent)' : '2px solid transparent',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
                    transition: 'color 0.15s',
                  }}
                >
                  <tab.icon size={13} />
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Panel Content */}
            <div style={{ flex: 1, overflow: 'hidden' }}>
              {rightPanel === 'activity' && <AgentActivity task={selectedTask} />}
              {rightPanel === 'files' && (
                <FileExplorer
                  tree={fileTree}
                  onFileSelect={handleFileSelect}
                  selectedFile={selectedFile}
                />
              )}
              {rightPanel === 'code' && (
                <div style={{ height: '100%', overflow: 'auto', padding: '12px' }}>
                  {fileContent ? (
                    <>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>
                        {selectedFile}
                        {fileContent.language && (
                          <span style={{ marginLeft: 8, color: 'var(--accent)' }}>
                            {fileContent.language}
                          </span>
                        )}
                      </div>
                      <pre className="font-mono" style={{
                        fontSize: 12, lineHeight: 1.6,
                        color: 'var(--text-primary)',
                        background: 'var(--bg-tertiary)',
                        borderRadius: 'var(--radius)', padding: 12,
                        overflow: 'auto',
                        border: '1px solid var(--border)',
                      }}>
                        {fileContent.content}
                      </pre>
                    </>
                  ) : (
                    <div style={{ color: 'var(--text-muted)', textAlign: 'center', paddingTop: 40, fontSize: 12 }}>
                      Select a file from the Files panel to view its content
                    </div>
                  )}
                </div>
              )}
              {rightPanel === 'chat' && <ChatPanel taskId={selectedTaskId || undefined} />}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
