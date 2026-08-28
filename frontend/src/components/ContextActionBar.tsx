import { useNavigate } from 'react-router-dom';
import { Term } from '@/components/Term';
import { recordTransition, NodeId } from '@/lib/usageTracker';

interface ContextActionBarProps {
  bookId: number;
  currentStep: string;
  suggestedActions: Array<{
    label: string;
    icon: string;
    tab: string;
    isAvailable?: () => boolean;
    onClick?: (bookId: number, currentStep: string) => void;
  }>;
}

export default function ContextActionBar({ bookId, currentStep, suggestedActions }: ContextActionBarProps) {
  const navigate = useNavigate();
  
  // Filter actions that are available
  const availableActions = suggestedActions.filter(action => 
    action.isAvailable ? action.isAvailable() : true
  );

  if (availableActions.length === 0) {
    return null;
  }

  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {availableActions.map((action, index) => (
        <button
          key={`${currentStep}-${action.tab}-${index}`}
          onClick={() => {
            if (action.onClick) {
              action.onClick(bookId, currentStep);
            } else {
              // Default action: navigate to the tab for the current step
              navigate(`/book/${bookId}/${currentStep}/${action.tab}`, { replace: true });
            }
            
            // Record transition from step to tab
            const fromNode: NodeId = `step-${currentStep}`;
            const toNode: NodeId = `tab-${action.tab}`;
            recordTransition(fromNode, toNode);
          }}
          className={`flex items-center space-x-2 px-3 py-1.5 rounded text-sm font-medium transition-colors hover:bg-[var(--bg-muted)] hover:text-[var(--text-primary)]`}
        >
          <span>{action.icon}</span>
          <Term term={action.label}>{action.label}</Term>
        </button>
      ))}
    </div>
  );
}