'use client';
import { useState, useEffect, useCallback } from 'react';
import { FileInfo, getFiles, getFileContent, deleteFile } from '@/lib/api';
import {
  Folder, FolderOpen, File, FileCode, FileText, RefreshCw, ChevronRight, Trash2, Plus
} from 'lucide-react';
import clsx from 'clsx';

interface FileExplorerProps {
  onFileSelect: (file: { path: string; content: string }) => void;
}

const EXT_ICONS: Record<string, React.ReactNode> = {
  '.py': <FileCode className="w-3.5 h-3.5 text-yellow-400" />,
  '.js': <FileCode className="w-3.5 h-3.5 text-yellow-300" />,
  '.ts': <FileCode className="w-3.5 h-3.5 text-blue-400" />,
  '.tsx': <FileCode className="w-3.5 h-3.5 text-blue-400" />,
  '.jsx': <FileCode className="w-3.5 h-3.5 text-cyan-400" />,
  '.go': <FileCode className="w-3.5 h-3.5 text-cyan-300" />,
  '.rs': <FileCode className="w-3.5 h-3.5 text-orange-400" />,
  '.md': <FileText className="w-3.5 h-3.5 text-slate-400" />,
  '.json': <FileCode className="w-3.5 h-3.5 text-green-400" />,
  '.sh': <FileCode className="w-3.5 h-3.5 text-green-300" />,
};

function getFileIcon(file: FileInfo): React.ReactNode {
  if (file.is_dir) return null;
  return EXT_ICONS[file.extension] || <File className="w-3.5 h-3.5 text-slate-500" />;
}

export default function FileExplorer({ onFileSelect }: FileExplorerProps) {
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [currentPath, setCurrentPath] = useState('.');
  const [pathHistory, setPathHistory] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const loadFiles = useCallback(async (path: string) => {
    setLoading(true);
    try {
      const data = await getFiles(path);
      setFiles(data);
      setCurrentPath(path);
    } catch (e) {
      console.error('Failed to load files:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFiles('.');
    const interval = setInterval(() => loadFiles(currentPath), 10000);
    return () => clearInterval(interval);
  }, [loadFiles]);

  const handleClick = async (file: FileInfo) => {
    if (file.is_dir) {
      const newPath = file.path;
      setPathHistory(prev => [...prev, currentPath]);
      await loadFiles(newPath);
    } else {
      setSelectedPath(file.path);
      try {
        const content = await getFileContent(file.path);
        onFileSelect({ path: file.path, content });
      } catch (e) {
        onFileSelect({ path: file.path, content: 'Failed to load file content' });
      }
    }
  };

  const handleBack = async () => {
    const prev = pathHistory[pathHistory.length - 1];
    if (prev !== undefined) {
      setPathHistory(h => h.slice(0, -1));
      await loadFiles(prev);
    }
  };

  const handleDelete = async (e: React.MouseEvent, file: FileInfo) => {
    e.stopPropagation();
    if (!confirm(`Delete ${file.name}?`)) return;
    try {
      await deleteFile(file.path);
      await loadFiles(currentPath);
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };

  const breadcrumbs = currentPath === '.' ? ['workspace'] : ['workspace', ...currentPath.split('/').filter(Boolean)];

  return (
    <div className="flex flex-col h-64 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-[#1e1e2e] bg-[#12121a] shrink-0">
        <FolderOpen className="w-3.5 h-3.5 text-yellow-500 shrink-0" />
        <span className="text-xs font-medium text-slate-400">Files</span>
        <div className="flex-1" />
        <button
          onClick={() => loadFiles(currentPath)}
          className="p-1 text-slate-600 hover:text-slate-300 transition-colors"
          title="Refresh"
        >
          <RefreshCw className={clsx('w-3 h-3', loading && 'animate-spin')} />
        </button>
      </div>

      {/* Breadcrumb */}
      <div className="flex items-center gap-1 px-3 py-1.5 text-xs text-slate-500 border-b border-[#1e1e2e] overflow-x-auto">
        {breadcrumbs.map((crumb, i) => (
          <span key={i} className="flex items-center gap-1 shrink-0">
            {i > 0 && <ChevronRight className="w-3 h-3" />}
            <span className={i === breadcrumbs.length - 1 ? 'text-slate-300' : 'hover:text-slate-300 cursor-pointer'}>
              {crumb}
            </span>
          </span>
        ))}
      </div>

      {/* File list */}
      <div className="flex-1 overflow-y-auto">
        {pathHistory.length > 0 && (
          <button
            onClick={handleBack}
            className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-slate-500 hover:bg-[#1a1a26] hover:text-slate-300 transition-colors text-left"
          >
            <Folder className="w-3.5 h-3.5" />
            ..
          </button>
        )}
        {files.length === 0 && !loading && (
          <div className="py-6 text-center text-xs text-slate-600">
            <Folder className="w-6 h-6 mx-auto mb-1 opacity-30" />
            <p>Empty directory</p>
          </div>
        )}
        {files.map(file => (
          <div
            key={file.path}
            onClick={() => handleClick(file)}
            className={clsx(
              'group flex items-center gap-2 px-3 py-1.5 text-xs cursor-pointer transition-colors',
              selectedPath === file.path
                ? 'bg-indigo-500/10 text-indigo-300'
                : 'text-slate-400 hover:bg-[#1a1a26] hover:text-slate-200'
            )}
          >
            <span className="shrink-0">
              {file.is_dir
                ? <Folder className="w-3.5 h-3.5 text-yellow-500/70" />
                : getFileIcon(file)
              }
            </span>
            <span className="flex-1 truncate">{file.name}</span>
            {!file.is_dir && (
              <span className="text-slate-600 shrink-0">
                {file.size < 1024 ? `${file.size}B` : `${(file.size / 1024).toFixed(1)}K`}
              </span>
            )}
            <button
              onClick={e => handleDelete(e, file)}
              className="opacity-0 group-hover:opacity-100 p-0.5 hover:text-red-400 transition-all shrink-0"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
