import { useNavigate } from 'react-router-dom';
import { WriteTab } from '@/components/tabs/WriteTab';
import ContextActionBar from '@/components/ContextActionBar';

export function WriteStep(_props: { bookId?: number; step?: string } = {}) {
  const navigate = useNavigate();
  const { bookId, step } = _props;
  const currentStep = step || 'write'; // fallback to 'write' if not provided
  
  const suggestedActions = [
    {
      label: 'スタイルラボでチェック',
      icon: '🧬',
      tab: 'style-lab',
      onClick: (bId: number, cStep: string) => {
        if (bId) {
          navigate(`/book/${bId}/${cStep}/style-lab`, { replace: true });
        }
      }
    },
    {
      label: 'プロットを確認',
      icon: '📖',
      tab: 'plots',
      onClick: (bId: number, cStep: string) => {
        if (bId) {
          navigate(`/book/${bId}/${cStep}/plots`, { replace: true });
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
      {bookId !== undefined && (
        <ContextActionBar bookId={bookId} currentStep={currentStep} suggestedActions={suggestedActions} />
      )}
    </div>
  );
}

export default WriteStep;