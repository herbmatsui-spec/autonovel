import { useNavigate } from 'react-router-dom';
import { PlanningTab } from '@/components/tabs/PlanningTab';
import ContextActionBar from '@/components/ContextActionBar';

export function ThemeStep(_props: { bookId?: number; step?: string } = {}) {
  const navigate = useNavigate();
  const { bookId, step } = _props;
  const currentStep = step || 'theme';
  
  const suggestedActions = [
    {
      label: 'スタイルラボで参照',
      icon: '🧬',
      tab: 'style-lab',
      onClick: (bId: number, cStep: string) => {
        if (bId) {
          navigate(`/book/${bId}/${cStep}/style-lab`, { replace: true });
        }
      }
    },
    {
      label: '市場分析を確認',
      icon: '📈',
      tab: 'analytics',
      onClick: (bId: number, cStep: string) => {
        if (bId) {
          navigate(`/book/${bId}/${cStep}/analytics`, { replace: true });
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
      {bookId !== undefined && (
        <ContextActionBar bookId={bookId} currentStep={currentStep} suggestedActions={suggestedActions} />
      )}
    </div>
  );
}

export default ThemeStep;