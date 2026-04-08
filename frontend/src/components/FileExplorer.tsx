import React, { useState } from 'react';
import { FolderOpen, File, ChevronRight, ChevronDown, Code } from 'lucide-react';
import type { FileNode } from '../utils/api';

interface FileExplorerProps {
  tree: FileNode | null;
  onFileSelect: (path: string) => void;
  selectedFile?: string;
}

const langColors: Record<string, string> = {
  python: '#3776ab',
  javascript: '#f7df1e',
  typescript: '#3178c6',
  go: '#00add8',
  rust: '#ce422b',
  java: '#007396',
  c: '#555555',
  cpp: '#00599c',
  bash: '#4eaa25',
  sql: '#e38c00',
};

function FileTreeNode({
  node,
  depth,
  onFileSelect,
  selectedFile,
}: {
  node: FileNode;
  depth: number;
  onFileSelect: (path: string) => void;
  selectedFile?: string;
}) {
  const [expanded, setExpanded] = useState(depth < 2);
  const isSelected = node.path === selectedFile;
  const color = node.language ? langColors[node.language] : undefined;

  const handleClick = () => {
    if (node.is_dir) {
      setExpanded(e => !e);
    } else {
      onFileSelect(node.path);
    }
  };

  return (
    <div>
      <div
        onClick={handleClick}
        style={{
          display: 'flex', alignItems: 'center', gap: 4,
          padding: '3px 8px', paddingLeft: `${8 + depth * 14}px`,
          cursor: 'pointer', borderRadius: 4,
          background: isSelected ? 'rgba(88,166,255,0.15)' : 'transparent',
          color: isSelected ? 'var(--accent)' : 'var(--text-primary)',
          fontSize: 13,
        }}
        onMouseEnter={e => {
          if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'var(--bg-hover)';
        }}
        onMouseLeave={e => {
          if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'transparent';
        }}
      >
        {node.is_dir ? (
          expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />
        ) : (
          <span style={{ width: 12 }} />
        )}
        {node.is_dir ? (
          <FolderOpen size={14} color="var(--warning)" />
        ) : (
          <File size={14} color={color || 'var(--text-secondary)'} />
        )}
        <span className="truncate" style={{ flex: 1 }}>{node.name}</span>
        {node.size != null && (
          <span style={{ fontSize: 10, color: 'var(--text-muted)', flexShrink: 0 }}>
            {node.size < 1024 ? `${node.size}B` : `${(node.size / 1024).toFixed(1)}K`}
          </span>
        )}
      </div>
      {node.is_dir && expanded && node.children?.map(child => (
        <FileTreeNode
          key={child.path}
          node={child}
          depth={depth + 1}
          onFileSelect={onFileSelect}
          selectedFile={selectedFile}
        />
      ))}
    </div>
  );
}

export const FileExplorer: React.FC<FileExplorerProps> = ({ tree, onFileSelect, selectedFile }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div className="panel-header">
        <div className="flex items-center gap-2">
          <FolderOpen size={14} />
          <span>File Explorer</span>
        </div>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 4px' }}>
        {!tree ? (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 24, fontSize: 12 }}>
            No project files yet
          </div>
        ) : (
          <FileTreeNode
            node={tree}
            depth={0}
            onFileSelect={onFileSelect}
            selectedFile={selectedFile}
          />
        )}
      </div>
    </div>
  );
};
