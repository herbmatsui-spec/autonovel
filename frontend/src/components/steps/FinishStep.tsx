import { useNavigate } from 'react-router-dom';
import { AuditTab } from '@/components/tabs/AuditTab';
import { AnalyticsTab } from '@/components/tabs/AnalyticsTab';
import ContextActionBar from '@/components/ContextActionBar';

export function FinishStep(_props: { bookId?: number; step?: string } = {}) {
  const navigate = useNavigate();
  const { bookId, step } = _props;
  const currentStep = step || 'finish';
  
  const suggestedActions = [
    {
      label: 'スタイルラボで最終チェック',
      icon: '🧬',
      tab: 'style-lab',
      onClick: (bId: number, cStep: string) => {
        if (bId) {
          navigate(`/book/${bId}/${cStep}/style-lab`, { replace: true });
        }
      }
    },
    {
      label: 'プロモーション素材を作成',
      icon: '🎨',
      tab: 'strategy', // Assuming strategy tab for promotion materials
      onClick: (bId: number, cStep: string) => {
        if (bId) {
          navigate(`/book/${bId}/${cStep}/strategy`, { replace: true });
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
      {bookId !== undefined && (
        <ContextActionBar bookId={bookId} currentStep={currentStep} suggestedActions={suggestedActions} />
      )}
    </div>
  );
}

export default FinishStep;