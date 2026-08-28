import { AuditTab } from '@/components/tabs/AuditTab';
import { AnalyticsTab } from '@/components/tabs/AnalyticsTab';
import ContextActionBar from '@/components/ContextActionBar';

export function FinishStep(_props: { bookId?: number; step?: string } = {}) {
  const { bookId, step } = _props;
  const currentStep = step || 'finish';
  
  const suggestedActions = [
    {
      label: 'スタイルラボで最終チェック',
      icon: '🧬',
      tab: 'style-lab',
      onClick: (bookId, currentStep) => {
        if (bookId) {
          navigate(`/book/${bookId}/${currentStep}/style-lab`, { replace: true });
        }
      }
    },
    {
      label: 'プロモーション素材を作成',
      icon: '🎨',
      tab: 'strategy', // Assuming strategy tab for promotion materials
      onClick: (bookId, currentStep) => {
        if (bookId) {
          navigate(`/book/${bookId}/${currentStep}/strategy`, { replace: true });
        }
      }
    }
  ];

  return (
    <div>
      <p className="text-sm text-muted-foreground mb-2">
        AIが仕上げをサポートします。よければ次へ進んでください。
      </p>
      <div className="space-y-6">
        <AuditTab />
        <AnalyticsTab />
      </div>
      <ContextActionBar bookId={bookId} currentStep={currentStep} suggestedActions={suggestedActions} />
    </div>
  );
}

export default FinishStep;