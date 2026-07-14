import React from 'react';
import { Button } from './button';

interface EmptyStateProps {
  icon: string;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div
      className="glass-panel"
      style={{
        textAlign: 'center',
        padding: '5rem 2rem',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '1rem',
        color: 'var(--text-muted)',
      }}
    >
      <span style={{ fontSize: '3rem' }}>{icon}</span>
      <h4 style={{ fontSize: '1.1rem', color: '#fff', margin: 0 }}>{title}</h4>
      {description && (
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: 0, maxWidth: '460px' }}>
          {description}
        </p>
      )}
      {action && (
        <Button onClick={action.onClick} style={{ marginTop: '0.5rem' }}>
          {action.label}
        </Button>
      )}
    </div>
  );
}
