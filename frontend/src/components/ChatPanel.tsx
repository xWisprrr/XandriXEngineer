import React, { useState } from 'react';
import { MessageSquare, Send, Loader } from 'lucide-react';
import { api } from '../utils/api';

interface ChatPanelProps {
  taskId?: string;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({ taskId }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: "Hi! I'm XandriX Engineer. Ask me anything about the current task or software engineering topics.",
      timestamp: new Date(),
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg: Message = { role: 'user', content: input, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const { response } = await api.chat(input, taskId);
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: response, timestamp: new Date() }
      ]);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: `Error: ${err instanceof Error ? err.message : 'Failed to get response'}`,
          timestamp: new Date(),
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="panel-header">
        <div className="flex items-center gap-2">
          <MessageSquare size={14} />
          <span>Chat</span>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              display: 'flex',
              flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
              gap: 8,
              alignItems: 'flex-start',
            }}
          >
            <div
              style={{
                width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
                background: msg.role === 'user' ? 'var(--accent)' : 'var(--purple)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 12, fontWeight: 700,
                color: 'var(--bg-primary)',
              }}
            >
              {msg.role === 'user' ? 'U' : 'X'}
            </div>
            <div
              style={{
                maxWidth: '80%', padding: '8px 12px', borderRadius: 'var(--radius)',
                background: msg.role === 'user' ? 'rgba(88,166,255,0.15)' : 'var(--bg-tertiary)',
                fontSize: 13, lineHeight: 1.5, color: 'var(--text-primary)',
                border: '1px solid var(--border)',
                whiteSpace: 'pre-wrap',
              }}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <div style={{
              width: 28, height: 28, borderRadius: '50%',
              background: 'var(--purple)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 12, fontWeight: 700, color: 'var(--bg-primary)',
            }}>X</div>
            <Loader size={14} color="var(--text-muted)" style={{ animation: 'spin 1s linear infinite' }} />
          </div>
        )}
      </div>

      <div style={{ padding: '12px 16px', borderTop: '1px solid var(--border)', display: 'flex', gap: 8 }}>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about the task... (Enter to send)"
          rows={2}
          style={{
            flex: 1, padding: '8px 12px',
            background: 'var(--bg-tertiary)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius)', color: 'var(--text-primary)',
            resize: 'none', fontSize: 13, lineHeight: 1.4,
          }}
        />
        <button
          className="btn btn-primary"
          onClick={handleSend}
          disabled={loading || !input.trim()}
          style={{ alignSelf: 'flex-end' }}
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  );
};
