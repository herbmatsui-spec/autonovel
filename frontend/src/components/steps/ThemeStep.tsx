import { PlanningTab } from '@/components/tabs/PlanningTab';
import ContextActionBar from '@/components/ContextActionBar';

export function ThemeStep(_props: { bookId?: number; step?: string } = {}) {
  const { bookId, step } = _props;
  const currentStep = step || 'theme';
  
  const suggestedActions = [
    {
      label: 'スタイルラボで参照',
      icon: '🧬',
      tab: 'style-lab',
      onClick: (bookId, currentStep) => {
        if (bookId) {
          navigate(`/book/${bookId}/${currentStep}/style-lab`, { replace: true });
        }
      }
    },
    {
      label: '市場分析を確認',
      icon: '📈',
      tab: 'analytics',
      onClick: (bookId, currentStep) => {
        if (bookId) {
          navigate(`/book/${bookId}/${currentStep}/analytics`, { replace: true });
        }
      }
    }
  ];

  return (
    <div>
      <p className="text-sm text-muted-foreground mb-2">
        AIが企画を下書きします。よければ次へ進んでください。
      </p>
      <PlanningTab />
      <ContextActionBar bookId={bookId} currentStep={currentStep} suggestedActions={suggestedActions} />
    </div>
  );
}

export default ThemeStep;