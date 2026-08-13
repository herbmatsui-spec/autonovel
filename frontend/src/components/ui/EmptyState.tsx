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
      className="glass-panel text-center py-[5rem] px-[2rem] flex flex-col items-center gap-[1rem] text-[var(--text-muted)]"
    >
      <span className="text-[3rem]">{icon}</span>
      <h4 className="text-[1.1rem] text-white m-0">{title}</h4>
      {description && (
        <p className="text-[0.85rem] text-[var(--text-secondary)] m-0 max-w-[460px]">
          {description}
        </p>
      )}
      {action && (
        <Button onClick={action.onClick} className="mt-[0.5rem]">
          {action.label}
        </Button>
      )}
    </div>
  );
}
