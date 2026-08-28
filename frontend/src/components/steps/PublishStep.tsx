import { useNavigate } from 'react-router-dom';
import { AnalyticsTab } from '@/components/tabs/AnalyticsTab';
import { StrategyTab } from '@/components/tabs/StrategyTab';
import ContextActionBar from '@/components/ContextActionBar';

export function PublishStep(_props: { bookId?: number; step?: string } = {}) {
  const navigate = useNavigate();
  const { bookId, step } = _props;
  const currentStep = step || 'publish';
  
  const suggestedActions = [
    {
      label: 'スタイルラボで最終確認',
      icon: '🧬',
      tab: 'style-lab',
      onClick: (bId: number, cStep: string) => {
        if (bId) {
          navigate(`/book/${bId}/${cStep}/style-lab`, { replace: true });
        }
      }
    },
    {
      label: '配信チャネルを設定',
      icon: '⚙️',
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
        AIが公開準備をサポートします。よければ次へ進んでください。
      </p>
      <div className="space-y-6">
        <AnalyticsTab />
        <StrategyTab />
      </div>
      {bookId !== undefined && (
        <ContextActionBar bookId={bookId} currentStep={currentStep} suggestedActions={suggestedActions} />
      )}
    </div>
  );
}

export default PublishStep;