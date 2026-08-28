import { useNavigate } from 'react-router-dom';
import { Term } from '@/components/Term';
import { getAssociationStrength, NodeId } from '@/lib/usageTracker';

interface StepBarProps {
  bookId: number;
  currentStep?: string;
  currentTab?: string;
}

export default function StepBar({ bookId, currentStep, currentTab: _currentTab }: StepBarProps) {
  const navigate = useNavigate();


  const steps = [
    { id: 'theme', label: 'テーマ', icon: '🎯' },
    { id: 'outline', label: 'あらすじ', icon: '📖' },
    { id: 'write', label: '執筆', icon: '✍️' },
    { id: 'finish', label: '仕上げ', icon: '✨' },
    { id: 'publish', label: '公開', icon: '🚀' },
  ];

  // Define related tabs for each step
  const functionTabs = [
    { id: 'style-lab', label: '文体ラボ', icon: '🧬' },
    { id: 'plots', label: 'プロット設計', icon: '📖' },
    { id: 'analytics', label: '品質＆販促', icon: '📈' },
    { id: 'audit', label: '品質監査', icon: '⚖️' },
    { id: 'monitor', label: '進捗モニター', icon: '📡' },
    { id: 'strategy', label: '戦略分析', icon: '📈' },
    { id: 'import', label: 'インポート', icon: '📥' },
  ];

  return (
    <div className="flex-shrink-0 w-[200px] bg-[var(--bg-sidebar)] border-r border-[var(--border)] p-4">
      <div className="space-y-2">
        {steps.map((step) => {
          const isCurrentStep = step.id === currentStep;
          
          // Calculate association strengths between this step and each function tab
          const tabAssociations: Array<{
            tab: typeof functionTabs[number];
            strength: number;
          }> = [];
          
          const stepNodeId: NodeId = `step-${step.id}`;
          
          functionTabs.forEach((tab) => {
            const tabNodeId: NodeId = `tab-${tab.id}`;
            const strength = getAssociationStrength(stepNodeId, tabNodeId);
            tabAssociations.push({ tab, strength });
          });
          
          // Sort by association strength descending
          tabAssociations.sort((a, b) => b.strength - a.strength);
          
          // Get the top 2 most associated tabs for display
          const topTabs = tabAssociations.slice(0, 2);
          
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
              title={topTabs.length > 0 ? `関連タブ: ${topTabs.map(t => `${t.tab.label} (${Math.round(t.strength * 100)}%)`).join(', ')}` : '関連データなし'}
            >
              <div className="flex items-center space-x-2">
                <span>{step.icon}</span>
                <Term term={step.label}>{step.label}</Term>
                {/* Show association strength for the most related tab if available */}
                {topTabs.length > 0 && topTabs[0].strength > 0 && (
                  <span className="text-xs bg-[var(--accent)]/20 text-[var(--accent)] rounded-full px-1.5">
                    {Math.round(topTabs[0].strength * 100)}%
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