import { useNavigate } from 'react-router-dom';
import { Term } from '@/components/Term';
import { recordTransition, NodeId } from '@/lib/usageTracker';

interface BookTabBarProps {
  bookId: number;
  currentStep: string;
  currentTab: string | null;
  onTabChange: (tab: string) => void;
}

export default function BookTabBar({ bookId, currentStep, currentTab, onTabChange }: BookTabBarProps) {
  const navigate = useNavigate();
  
  // Define tabs that are available in the book workspace context
  // We can filter by step if needed, but for now show all
  const tabs = [
    { id: 'style-lab', label: '文体ラボ', icon: '🧬' },
    { id: 'plots', label: 'プロット設計', icon: '📖' },
    { id: 'analytics', label: '品質＆販促', icon: '📈' },
    { id: 'story-canvas', label: 'ストーリーキャンバス', icon: '🗺️' },
    { id: 'consistency', label: '整合性', icon: '🛡️' },
    { id: 'workspace', label: 'ワークスペース', icon: '📁' },
    // Add more tabs as needed
  ];

  const handleTabClick = (tabId: string) => {
    onTabChange(tabId);
    // Update URL to include the tab, keeping the current step
    navigate(`/book/${bookId}/${currentStep}/${tabId}`, { replace: true });
    
    // Record transition
    const fromNode: NodeId = currentTab ? `tab-${currentTab}` : `step-${currentStep}`;
    const toNode: NodeId = `tab-${tabId}`;
    recordTransition(fromNode, toNode);
  };

  return (
    <div className="mb-4 border-b border-[var(--border)] pb-2">
      <div className="flex flex-wrap gap-2">
        {tabs.map((tab) => {
          const isActive = tab.id === currentTab;
          return (
            <button
              key={tab.id}
              onClick={() => handleTabClick(tab.id)}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-[var(--accent)]/20 text-[var(--accent)] border border-[var(--accent)]/30'
                  : 'text-[var(--text-secondary)] hover:bg-[var(--bg-muted)] hover:text-[var(--text-primary)]'
              }`}
            >
              <span>{tab.icon}</span>
              <Term term={tab.label}>{tab.label}</Term>
            </button>
          );
        })}
      </div>
    </div>
  );
}