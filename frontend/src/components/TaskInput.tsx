import React, { useState } from 'react';
import { Send, Plus, Loader } from 'lucide-react';
import { api } from '../utils/api';

interface TaskInputProps {
  onTaskCreated: (taskId: string) => void;
}

const EXAMPLE_TASKS = [
  'Build a REST API in Python with FastAPI that manages a todo list with CRUD operations',
  'Create a React TypeScript todo app with filtering and local storage persistence',
  'Write a Go HTTP server that serves a JSON API for user management',
  'Build a CLI tool in Python that converts CSV files to JSON format',
  'Create a Rust program that implements a binary search tree',
];

export const TaskInput: React.FC<TaskInputProps> = ({ onTaskCreated }) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [language, setLanguage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showExamples, setShowExamples] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) return;

    setLoading(true);
    setError('');
    try {
      const task = await api.createTask(title, description, language || undefined);
      onTaskCreated(task.id);
      setTitle('');
      setDescription('');
      setLanguage('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create task');
    } finally {
      setLoading(false);
    }
  };

  const useExample = (example: string) => {
    setTitle(example.slice(0, 60));
    setDescription(example);
    setShowExamples(false);
  };

  return (
    <form onSubmit={handleSubmit} style={{ padding: '20px' }}>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>New Task</h2>
        <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          Describe what you want XandriX to build
        </p>
      </div>

      {error && (
        <div style={{
          background: 'rgba(248,81,73,0.1)', border: '1px solid var(--error)',
          borderRadius: 'var(--radius)', padding: '8px 12px', marginBottom: 12,
          color: 'var(--error)', fontSize: 12,
        }}>
          {error}
        </div>
      )}

      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
          Title
        </label>
        <input
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="e.g., Build a REST API"
          style={{
            width: '100%', padding: '8px 12px',
            background: 'var(--bg-tertiary)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius)', color: 'var(--text-primary)',
          }}
          required
        />
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
          Description
        </label>
        <textarea
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder="Describe the task in detail..."
          rows={5}
          style={{
            width: '100%', padding: '8px 12px',
            background: 'var(--bg-tertiary)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius)', color: 'var(--text-primary)',
            resize: 'vertical', lineHeight: 1.5,
          }}
          required
        />
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
          Language (optional)
        </label>
        <select
          value={language}
          onChange={e => setLanguage(e.target.value)}
          style={{
            width: '100%', padding: '8px 12px',
            background: 'var(--bg-tertiary)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius)', color: 'var(--text-primary)',
          }}
        >
          <option value="">Auto-detect</option>
          <option value="python">Python</option>
          <option value="javascript">JavaScript</option>
          <option value="typescript">TypeScript</option>
          <option value="go">Go</option>
          <option value="rust">Rust</option>
          <option value="java">Java</option>
          <option value="c">C</option>
          <option value="cpp">C++</option>
          <option value="bash">Bash</option>
          <option value="sql">SQL</option>
        </select>
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <button type="submit" className="btn btn-primary" style={{ flex: 1 }} disabled={loading}>
          {loading ? <Loader size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Send size={14} />}
          {loading ? 'Starting...' : 'Run Task'}
        </button>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => setShowExamples(s => !s)}
        >
          <Plus size={14} />
        </button>
      </div>

      {showExamples && (
        <div style={{ marginTop: 12, borderTop: '1px solid var(--border)', paddingTop: 12 }}>
          <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>Examples:</p>
          {EXAMPLE_TASKS.map((ex, i) => (
            <button
              key={i}
              type="button"
              onClick={() => useExample(ex)}
              style={{
                display: 'block', width: '100%', textAlign: 'left',
                padding: '6px 8px', marginBottom: 4, fontSize: 12,
                background: 'var(--bg-tertiary)', border: '1px solid var(--border)',
                borderRadius: 4, color: 'var(--text-secondary)', cursor: 'pointer',
              }}
              onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-primary)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
            >
              {ex}
            </button>
          ))}
        </div>
      )}
    </form>
  );
};
