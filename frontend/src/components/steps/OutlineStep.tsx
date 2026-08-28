import { useNavigate } from 'react-router-dom';
import { PlotsTab } from '@/components/tabs/PlotsTab';
import ContextActionBar from '@/components/ContextActionBar';

export function OutlineStep(_props: { bookId?: number; step?: string } = {}) {
  const navigate = useNavigate();
  const { bookId, step } = _props;
  const currentStep = step || 'outline';
  
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
      label: 'キャラクター詳細を編集',
      icon: '👥',
      tab: 'books',
      onClick: (bId: number, _cStep: string) => {
        if (bId) {
          navigate(`/books`, { replace: true });
        }
      }
    }
  ];

  return (
    <div>
      <p className="text-sm text-muted-foreground mb-2">
        AIがプロットを下書きします。よければ次へ進んでください。
      </p>
      <PlotsTab />
      {bookId !== undefined && (
        <ContextActionBar bookId={bookId} currentStep={currentStep} suggestedActions={suggestedActions} />
      )}
    </div>
  );
}

export default OutlineStep;