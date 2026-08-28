import { WriteTab } from '@/components/tabs/WriteTab';
import ContextActionBar from '@/components/ContextActionBar';

export function WriteStep(_props: { bookId?: number; step?: string } = {}) {
  const { bookId, step } = _props;
  const currentStep = step || 'write'; // fallback to 'write' if not provided
  
  const suggestedActions = [
    {
      label: 'スタイルラボでチェック',
      icon: '🧬',
      tab: 'style-lab',
      onClick: (bookId, currentStep) => {
        if (bookId) {
          navigate(`/book/${bookId}/${currentStep}/style-lab`, { replace: true });
        }
      }
    },
    {
      label: 'プロットを確認',
      icon: '📖',
      tab: 'plots',
      onClick: (bookId, currentStep) => {
        if (bookId) {
          navigate(`/book/${bookId}/${currentStep}/plots`, { replace: true });
        }
      }
    }
  ];

  return (
    <div>
      <p className="text-sm text-muted-foreground mb-2">
        AIが本文を下書きします。よければ次へ進んでください。
      </p>
      <WriteTab />
      <ContextActionBar bookId={bookId} currentStep={currentStep} suggestedActions={suggestedActions} />
    </div>
  );
}

export default WriteStep;