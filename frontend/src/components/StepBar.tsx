import { useNavigate } from 'react-router-dom';
import { Term } from '@/components/Term';

interface StepBarProps {
  bookId: number;
  currentStep?: string;
  currentTab?: string;
}

export default function StepBar({ bookId, currentStep, currentTab }: StepBarProps) {
  const navigate = useNavigate();
  const steps = [
    { id: 'theme', label: 'テーマ', icon: '🎯' },
    { id: 'outline', label: 'あらすじ', icon: '📖' },
    { id: 'write', label: '執筆', icon: '✍️' },
    { id: 'finish', label: '仕上げ', icon: '✨' },
    { id: 'publish', label: '公開', icon: '🚀' },
  ];

  // Define related tabs for each step
  const stepTabRelations: Record<string, string[]> = {
    theme: ['style-lab', 'analytics'],
    outline: ['plots', 'strategy'],
    write: ['style-lab', 'plots'],
    finish: ['style-lab', 'analytics'],
    publish: ['analytics', 'strategy'],
  };

  return (
    <div className="flex-shrink-0 w-[200px] bg-[var(--bg-sidebar)] border-r border-[var(--border)] p-4">
      <div className="space-y-2">
        {steps.map((step) => {
          const isCurrentStep = step.id === currentStep;
          const relatedTabs = stepTabRelations[step.id] || [];
          const isCurrentTab = currentTab && relatedTabs.includes(currentTab);
          
          return (
            <button
              key={step.id}
              onClick={() => {
                if (bookId) {
                  navigate(`/book/${bookId}/${step.id}`, { replace: true });
                }
              }}
              className={`w-full text-left justify-start flex items-center space-x-3 p-2 rounded ${
                isCurrentStep
                  ? 'bg-[var(--accent)]/20 text-[var(--accent)]'
                  : 'text-[var(--text-secondary)] hover:bg-[var(--bg-muted)]'
              }`}
              title={relatedTabs.length > 0 ? `関連タブ: ${relatedTabs.map(t => t).join(', ')}` : undefined}
            >
              <div className="flex items-center space-x-2">
                <span>{step.icon}</span>
                <Term term={step.label}>{step.label}</Term>
                {/* Show current tab badge if the current tab is one of the related tabs for this step */}
                {currentTab && isCurrentStep && relatedTabs.includes(currentTab) && (
                  <span className="text-xs bg-[var(--accent)]/20 text-[var(--accent)] rounded-full px-1.5">
                    <Term term={currentTab}>{currentTab}</Term>
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}