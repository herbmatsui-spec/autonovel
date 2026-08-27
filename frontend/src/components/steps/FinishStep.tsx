import { AuditTab } from '@/components/tabs/AuditTab';
import { AnalyticsTab } from '@/components/tabs/AnalyticsTab';

export function FinishStep(_props: { bookId?: number } = {}) {
  return (
    <div>
      <p className="text-sm text-muted-foreground mb-2">
        AIが仕上げをサポートします。よければ次へ進んでください。
      </p>
      <div className="space-y-6">
        <AuditTab />
        <AnalyticsTab />
      </div>
    </div>
  );
}

export default FinishStep;