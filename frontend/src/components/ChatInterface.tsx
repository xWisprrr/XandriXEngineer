'use client';
import { useState, useRef, useEffect, useCallback } from 'react';
import {
  sendChatMessage,
  Task,
  ChatResponse,
  ActionItem,
} from '@/lib/api';
import {
  Send,
  Loader2,
  Bot,
  User,
  Zap,
  Code2,
  TestTube2,
  Settings,
  ChevronDown,
  Sparkles,
} from 'lucide-react';
import clsx from 'clsx';

// ─── Types ─────────────────────────────────────────────────────────────────

interface ChatBubble {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  response?: ChatResponse;
}

interface ChatInterfaceProps {
  onTaskCreated: (task: Task) => void;
  currentProjectId: string | null;
  onProjectCreated: (projectId: string) => void;
}

// ─── Helpers ───────────────────────────────────────────────────────────────

const ACTION_ICONS: Record<string, React.ReactNode> = {
  architecture_design: <Settings className="w-3 h-3" />,
  code_generation: <Code2 className="w-3 h-3" />,
  testing: <TestTube2 className="w-3 h-3" />,
  execution: <Zap className="w-3 h-3" />,
  modification: <Sparkles className="w-3 h-3" />,
};

const ACTION_COLORS: Record<string, string> = {
  architecture_design: 'text-purple-400 bg-purple-400/10 border-purple-400/20',
  code_generation: 'text-blue-400 bg-blue-400/10 border-blue-400/20',
  testing: 'text-green-400 bg-green-400/10 border-green-400/20',
  execution: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20',
  modification: 'text-orange-400 bg-orange-400/10 border-orange-400/20',
};

const INTENT_LABELS: Record<string, string> = {
  new_project: '🚀 New Project',
  modification: '✏️ Modification',
  clarification: '❓ Clarification',
};

const EXAMPLE_PROMPTS = [
  'Build a production-grade SaaS application called TaskFlow with authentication, database persistence, and a modern dashboard UI.',
  'Create a REST API in Python with FastAPI that has CRUD endpoints for a todo list, including tests.',
  'Build a real-time chat app with WebSocket support and a React frontend.',
];

let idCounter = 0;
const makeId = () => `msg_${++idCounter}_${Date.now()}`;

// ─── Action Plan Card ──────────────────────────────────────────────────────

function ActionPlan({ response }: { response: ChatResponse }) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="mt-2 rounded-lg border border-[#2a2a40] bg-[#13131f] overflow-hidden text-xs">
      <button
        onClick={() => setExpanded(v => !v)}
        className="w-full flex items-center justify-between px-3 py-2 text-slate-400 hover:text-slate-300 transition-colors"
      >
        <span className="font-medium flex items-center gap-2">
          <span className="text-indigo-400">{INTENT_LABELS[response.intent] ?? response.intent}</span>
          <span className="text-slate-600">·</span>
          <span>{response.actions.length} action{response.actions.length !== 1 ? 's' : ''}</span>
          {response.task_id && (
            <>
              <span className="text-slate-600">·</span>
              <span className="text-green-400">Task queued</span>
            </>
          )}
        </span>
        <ChevronDown className={clsx('w-3.5 h-3.5 transition-transform', expanded ? 'rotate-180' : '')} />
      </button>

      {expanded && (
        <div className="px-3 pb-3 space-y-1.5 border-t border-[#2a2a40]">
          {/* Actions */}
          {response.actions.map((action, i) => (
            <ActionBadge key={i} action={action} index={i} />
          ))}

          {/* Affected files (modifications only) */}
          {response.affected_files.length > 0 && (
            <div className="mt-2 pt-2 border-t border-[#2a2a40]">
              <p className="text-slate-500 mb-1">Affected files:</p>
              <div className="flex flex-wrap gap-1">
                {response.affected_files.slice(0, 6).map(f => (
                  <span
                    key={f}
                    className="px-1.5 py-0.5 rounded bg-[#1a1a2e] text-slate-400 font-mono text-[10px] border border-[#2a2a40]"
                  >
                    {f}
                  </span>
                ))}
                {response.affected_files.length > 6 && (
                  <span className="text-slate-600 text-[10px]">+{response.affected_files.length - 6} more</span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ActionBadge({ action, index }: { action: ActionItem; index: number }) {
  const colorClass = ACTION_COLORS[action.type] ?? 'text-slate-400 bg-slate-400/10 border-slate-400/20';
  const icon = ACTION_ICONS[action.type] ?? <Zap className="w-3 h-3" />;

  return (
    <div className="flex items-start gap-2 mt-1.5">
      <span className="text-slate-600 w-4 text-right shrink-0 mt-0.5">{index + 1}.</span>
      <span className={clsx('inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[10px] font-medium shrink-0', colorClass)}>
        {icon}
        {action.type.replace(/_/g, ' ')}
      </span>
      <span className="text-slate-400 leading-relaxed">
        {action.target && <span className="text-slate-300">{action.target}: </span>}
        {action.goal}
      </span>
    </div>
  );
}

// ─── Chat Bubble ───────────────────────────────────────────────────────────

function Bubble({ bubble }: { bubble: ChatBubble }) {
  const isUser = bubble.role === 'user';
  return (
    <div className={clsx('flex gap-3', isUser ? 'justify-end' : 'justify-start')}>
      {!isUser && (
        <div className="w-7 h-7 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center shrink-0 mt-0.5">
          <Bot className="w-4 h-4 text-indigo-400" />
        </div>
      )}
      <div className={clsx('max-w-[82%]', isUser ? 'items-end' : 'items-start', 'flex flex-col gap-1')}>
        <div
          className={clsx(
            'px-3 py-2 rounded-xl text-sm leading-relaxed',
            isUser
              ? 'bg-indigo-600 text-white rounded-tr-sm'
              : 'bg-[#1a1a2e] text-slate-200 border border-[#2a2a40] rounded-tl-sm',
          )}
        >
          {bubble.content}
        </div>
        {bubble.response && <ActionPlan response={bubble.response} />}
        <span className="text-[10px] text-slate-600">{bubble.timestamp}</span>
      </div>
      {isUser && (
        <div className="w-7 h-7 rounded-lg bg-slate-700/50 border border-slate-600/30 flex items-center justify-center shrink-0 mt-0.5">
          <User className="w-4 h-4 text-slate-400" />
        </div>
      )}
    </div>
  );
}

// ─── Main Component ────────────────────────────────────────────────────────

export default function ChatInterface({
  onTaskCreated,
  currentProjectId,
  onProjectCreated,
}: ChatInterfaceProps) {
  const [bubbles, setBubbles] = useState<ChatBubble[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [projectId, setProjectId] = useState<string | null>(currentProjectId);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Sync project id from parent
  useEffect(() => {
    setProjectId(currentProjectId);
  }, [currentProjectId]);

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [bubbles]);

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setInput('');
    setError(null);
    setLoading(true);

    // Optimistically add user bubble
    const userBubble: ChatBubble = {
      id: makeId(),
      role: 'user',
      content: trimmed,
      timestamp: new Date().toLocaleTimeString(),
    };
    setBubbles(prev => [...prev, userBubble]);

    try {
      const response = await sendChatMessage(trimmed, projectId ?? undefined);

      // Update project id
      if (!projectId && response.project_id) {
        setProjectId(response.project_id);
        onProjectCreated(response.project_id);
      }

      // Add assistant bubble
      const assistantBubble: ChatBubble = {
        id: makeId(),
        role: 'assistant',
        content: response.summary || response.message,
        timestamp: new Date().toLocaleTimeString(),
        response,
      };
      setBubbles(prev => [...prev, assistantBubble]);

      // Notify parent about the task so existing panels update
      if (response.task_id) {
        onTaskCreated({
          id: response.task_id,
          title: response.task_title,
          description: trimmed,
          status: 'pending',
          created_at: new Date().toISOString(),
          steps: [],
          current_step: 0,
          priority: 5,
          logs: [],
        });
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Request failed';
      setError(msg);
      setBubbles(prev => [
        ...prev,
        {
          id: makeId(),
          role: 'assistant',
          content: `⚠️ ${msg}`,
          timestamp: new Date().toLocaleTimeString(),
        },
      ]);
    } finally {
      setLoading(false);
      textareaRef.current?.focus();
    }
  }, [loading, projectId, onProjectCreated, onTaskCreated]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {bubbles.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-6 py-8">
            <div className="w-14 h-14 rounded-2xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center">
              <Bot className="w-7 h-7 text-indigo-400" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white mb-1">XandriXEngineer</h2>
              <p className="text-sm text-slate-500 max-w-xs">
                Your autonomous AI software engineer. Describe what you want to build.
              </p>
            </div>
            <div className="w-full max-w-lg space-y-2">
              <p className="text-xs text-slate-600 uppercase tracking-widest">Example prompts</p>
              {EXAMPLE_PROMPTS.map((prompt, i) => (
                <button
                  key={i}
                  onClick={() => sendMessage(prompt)}
                  className="w-full text-left px-3 py-2.5 rounded-lg bg-[#1a1a2e] border border-[#2a2a40] text-xs text-slate-400 hover:text-slate-200 hover:border-indigo-500/40 transition-all"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {bubbles.map(bubble => (
          <Bubble key={bubble.id} bubble={bubble} />
        ))}

        {loading && (
          <div className="flex gap-3 justify-start">
            <div className="w-7 h-7 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center shrink-0">
              <Bot className="w-4 h-4 text-indigo-400" />
            </div>
            <div className="px-3 py-2 rounded-xl bg-[#1a1a2e] border border-[#2a2a40] rounded-tl-sm">
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-[#1e1e2e] bg-[#12121a] px-4 py-3">
        {error && (
          <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-md px-3 py-1.5 mb-2">
            {error}
          </p>
        )}

        {projectId && (
          <div className="text-[10px] text-slate-600 mb-1.5 font-mono">
            Project: {projectId.slice(0, 8)}…
            {bubbles.length > 0 && ' · Follow-up changes will be applied incrementally'}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex items-end gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              projectId
                ? 'Send a follow-up (e.g. "make the UI dark mode", "add task priorities")…'
                : 'Describe what you want to build…'
            }
            rows={2}
            disabled={loading}
            className="flex-1 bg-[#1a1a26] border border-[#2a2a40] rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 resize-none transition-all disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className={clsx(
              'flex items-center justify-center w-9 h-9 rounded-lg transition-all shrink-0',
              loading || !input.trim()
                ? 'bg-indigo-500/20 text-indigo-400/50 cursor-not-allowed'
                : 'bg-indigo-500 hover:bg-indigo-600 text-white shadow-lg shadow-indigo-500/20',
            )}
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </form>
        <p className="text-[10px] text-slate-600 mt-1.5">⌘ + Enter to send</p>
      </div>
    </div>
  );
}
