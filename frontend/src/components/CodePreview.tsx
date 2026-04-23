'use client';
import { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check, FileCode, X } from 'lucide-react';

interface CodePreviewProps {
  path: string;
  content: string;
  onClose?: () => void;
}

const EXT_LANGUAGE: Record<string, string> = {
  '.py': 'python',
  '.js': 'javascript',
  '.mjs': 'javascript',
  '.ts': 'typescript',
  '.tsx': 'tsx',
  '.jsx': 'jsx',
  '.go': 'go',
  '.rs': 'rust',
  '.java': 'java',
  '.c': 'c',
  '.cpp': 'cpp',
  '.sh': 'bash',
  '.bash': 'bash',
  '.json': 'json',
  '.yaml': 'yaml',
  '.yml': 'yaml',
  '.toml': 'toml',
  '.md': 'markdown',
  '.html': 'html',
  '.css': 'css',
  '.sql': 'sql',
};

function getLanguage(path: string): string {
  const ext = '.' + path.split('.').pop()?.toLowerCase();
  return EXT_LANGUAGE[ext] || 'text';
}

export default function CodePreview({ path, content, onClose }: CodePreviewProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error('Copy failed:', e);
    }
  };

  const language = getLanguage(path);
  const filename = path.split('/').pop() || path;
  const lineCount = content.split('\n').length;

  return (
    <div className="flex flex-col h-full bg-[#0d0d15] overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-[#1e1e2e] bg-[#12121a] shrink-0">
        <FileCode className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
        <span className="text-xs text-slate-300 font-mono truncate flex-1" title={path}>
          {filename}
        </span>
        <span className="text-xs text-slate-600 shrink-0">{lineCount} lines</span>
        <button
          onClick={handleCopy}
          className="p-1 text-slate-600 hover:text-slate-300 transition-colors"
          title="Copy code"
        >
          {copied ? (
            <Check className="w-3.5 h-3.5 text-green-400" />
          ) : (
            <Copy className="w-3.5 h-3.5" />
          )}
        </button>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 text-slate-600 hover:text-slate-300 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Language badge */}
      <div className="px-3 py-1 border-b border-[#1e1e2e] bg-[#0f0f1a]">
        <span className="text-xs text-indigo-400/70 font-mono">{language}</span>
        <span className="text-xs text-slate-600 ml-2 font-mono">{path}</span>
      </div>

      {/* Code content */}
      <div className="flex-1 overflow-auto text-xs">
        <SyntaxHighlighter
          language={language}
          style={vscDarkPlus}
          showLineNumbers
          wrapLongLines={false}
          customStyle={{
            margin: 0,
            padding: '12px',
            background: 'transparent',
            fontSize: '0.78rem',
            lineHeight: '1.5',
            minHeight: '100%',
          }}
          lineNumberStyle={{
            color: '#334155',
            paddingRight: '12px',
            minWidth: '2.5em',
            userSelect: 'none',
          }}
        >
          {content}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}
