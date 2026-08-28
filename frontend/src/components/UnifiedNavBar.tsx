import { useNavigate } from 'react-router-dom';
import { useBookStore } from '@/store/useBookStore';
import { useWorkspaceStore } from '@/store/useWorkspaceStore';
import { Term } from '@/components/Term';

export default function UnifiedNavBar() {
  const navigate = useNavigate();
  const { selectedBook } = useBookStore();
  const { currentStep: rawCurrentStep } = useWorkspaceStore();
  const currentStep = rawCurrentStep || 'theme';
  
  // If no book is selected, show a simplified view or redirect
  if (!selectedBook) {
    return (
      <div className="hidden">
        {/* No book selected - could show a message or redirect */}
        <div className="p-4 text-center">
          <p className="text-[var(--text-secondary)]">作品を選択してください</p>
        </div>
      </div>
    );
  }

  // Define the steps (vertical timeline)
  const steps = [
    { id: 'theme', label: 'テーマ', icon: '🎯' },
    { id: 'outline', label: 'あらすじ', icon: '📖' },
    { id: 'write', label: '執筆', icon: '✍️' },
    { id: 'finish', label: '仕上げ', icon: '✨' },
    { id: 'publish', label: '公開', icon: '🚀' },
  ];

  // Define the function tabs (horizontal stream)
  // These are the tabs available when viewing a book
  const functionTabs = [
    { id: 'style-lab', label: '文体ラボ', icon: '🧬' },
    { id: 'plots', label: 'プロット設計', icon: '📖' },
    { id: 'analytics', label: '品質＆販促', icon: '📈' },
    { id: 'audit', label: '品質監査', icon: '⚖️' },
    { id: 'monitor', label: '進捗モニター', icon: '📡' },
    { id: 'strategy', label: '戦略分析', icon: '📈' },
    { id: 'import', label: 'インポート', icon: '📥' },
  ];

  // Determine which tabs are relevant for the current step
  // This could be based on a predefined matrix or usage data
  const stepTabRelevance: Record<string, string[]> = {
    theme: ['style-lab', 'analytics'],
    outline: ['plots', 'strategy'],
    write: ['style-lab', 'plots', 'analytics'],
    finish: ['style-lab', 'analytics', 'audit'],
    publish: ['analytics', 'strategy', 'style-lab'],
  };

  const relevantTabs = stepTabRelevance[currentStep] || functionTabs.map(t => t.id);

  return (
    <div className="flex h-[calc(100vh_-5rem)]">
      {/* Vertical Step Timeline */}
      <div className="flex-shrink-0 w-[200px] bg-[var(--bg-sidebar)] border-r border-[var(--border)] p-4 overflow-y-auto">
        <div className="space-y-2">
          {steps.map((step) => {
            const isCurrentStep = step.id === currentStep;
            const completedSteps = ['theme', 'outline', 'write', 'finish']; // This would come from state
            const isCompleted = 
              completedSteps.indexOf(step.id) < completedSteps.indexOf(currentStep) && 
              currentStep !== step.id;
            
            return (
              <div key={step.id} className="flex items-center space-x-3 p-2 rounded">
                <div className="flex-shrink-0">
                  <span className={`${isCurrentStep ? 'text-[var(--accent)]' : isCompleted ? 'text-[var(--text-muted)]' : 'text-[var(--text-secondary)]'}`}>
                    {step.icon}
                  </span>
                </div>
                <div className="flex-1">
                  <Term term={step.label} className={`${isCurrentStep ? 'font-medium text-[var(--text-primary)]' : isCompleted ? 'text-[var(--text-muted)]' : 'text-[var(--text-secondary)]'}`}>
                    {step.label}
                  </Term>
                  {/* Show progress indicator for current step */}
                  {isCurrentStep && (
                    <div className="w-full h-0.5 bg-[var(--accent)]/20 mt-1">
                      <div className="h-full bg-[var(--accent)] w-[60%]"></div>
                    </div>
                  )}
                </div>
                {/* Show relevant tabs for this step as small indicators */}
                <div className="flex space-x-1 text-xs">
                  {relevantTabs.map((tabId: string) => {
                    const tab = functionTabs.find(t => t.id === tabId);
                    if (!tab) return null;
                    const isCurrentTab = false; // We don't have current tab in this context - would need to be passed
                    
                    return (
                      <div 
                        key={tabId}
                        className={`flex items-center justify-center w-5 h-5 rounded ${
                          isCurrentTab 
                            ? 'bg-[var(--accent)]/20 text-[var(--accent)]' 
                            : 'bg-[var(--bg-muted)]/50 text-[var(--text-secondary)] hover:bg-[var(--bg-muted)]'
                        }`}
                        title={tab.label}
                      >
                        <span>{tab.icon}</span>
                      </div>
                    );
                  }).filter(Boolean)}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Main Content Area with Horizontal Tab Stream */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Tab Stream (horizontal) */}
        <div className="flex-shrink-0 h-[44px] bg-[var(--bg-muted)] border-b border-[var(--border)] px-4 flex items-center">
          <div className="flex-1 overflow-x-auto space-x-2">
            {functionTabs.map((tab) => {
              // Only show tabs that are relevant for current step
              if (!relevantTabs.includes(tab.id)) {
                return null;
              }
              
              // We don't have the current tab from URL here - would need to parse it
              // For now, we'll highlight based on a placeholder - in reality this would come from URL params
              const isActive = false; // Placeholder
              
              return (
                <button
                  key={tab.id}
                  onClick={() => {
                    // Navigate to the tab for current book and step
                    if (selectedBook?.id) {
                      navigate(`/book/${selectedBook.id}/${currentStep}/${tab.id}`, { replace: true });
                    }
                  }}
                  className={`flex items-center space-x-2 px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-[var(--accent)]/20 text-[var(--accent)] border border-[var(--accent)]/30'
                      : 'text-[var(--text-secondary)] hover:bg-[var(--bg-muted)] hover:text-[var(--text-primary)]'
                  }`}
                >
                  <span>{tab.icon}</span>
                  <span className="hidden md:inline">
                    <Term term={tab.label}>{tab.label}</Term>
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-hidden">
          {/* This would be replaced by Outlet or specific content based on step/tab */}
          <div className="p-6">
            <div className="space-y-4">
              <h2 className="text-xl font-bold">
                <Term term="統一ナビゲーションバー">{'統一ナビゲーションバー'}</Term>
              </h2>
              <p className="text-[var(--text-secondary)]">
                ステップ（縦）と機能タブ（横）を組み合わせたナビゲーションインターフェース
              </p>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-[var(--bg-muted)] p-4 rounded">
                  <h3 className="font-medium mb-2">現在のステップ:</h3>
                  <p className="text-[var(--accent)] font-medium">
                    <Term term={steps.find(s => s.id === currentStep)?.label || currentStep}>
                      {steps.find(s => s.id === currentStep)?.label || currentStep}
                    </Term>
                  </p>
                </div>
                <div className="bg-[var(--bg-muted)] p-4 rounded">
                  <h3 className="font-medium mb-2">関連機能タブ:</h3>
                  <div className="flex flex-wrap gap-2">
                    {relevantTabs.map((tabId: string) => {
                      const tab = functionTabs.find(t => t.id === tabId);
                      if (!tab) return null;
                      return (
                        <div key={tab.id} className="flex items-center space-x-1 px-2 py-1 bg-[var(--accent)]/10 text-[var(--accent)] rounded text-xs">
                          <span>{tab.icon}</span>
                          <Term term={tab.label}>{tab.label}</Term>
                        </div>
                      );
                    }).filter(Boolean)}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}