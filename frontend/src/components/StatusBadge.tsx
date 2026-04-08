import React from 'react';
import type { TaskStatus } from '../utils/api';

interface StatusBadgeProps {
  status: TaskStatus;
}

const statusConfig: Record<TaskStatus, { label: string; pulse?: boolean }> = {
  pending: { label: 'Pending' },
  planning: { label: 'Planning', pulse: true },
  running: { label: 'Running', pulse: true },
  paused: { label: 'Paused' },
  completed: { label: 'Completed' },
  failed: { label: 'Failed' },
  cancelled: { label: 'Cancelled' },
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const config = statusConfig[status] || { label: status };
  return (
    <span className={`badge badge-${status}`}>
      {config.pulse && (
        <span className={`pulse-dot pulse-${status}`} />
      )}
      {config.label}
    </span>
  );
};
