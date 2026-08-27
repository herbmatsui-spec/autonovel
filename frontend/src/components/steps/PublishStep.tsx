import { AnalyticsTab } from '@/components/tabs/AnalyticsTab';
import { StrategyTab } from '@/components/tabs/StrategyTab';

export function PublishStep({ bookId: _bookId }: { bookId?: number } = {}) {
  return (
    <div>
      <p className="text-sm text-muted-foreground mb-2">
        AIが公開準備をサポートします。よければ次へ進んでください。
      </p>
      <div className="space-y-6">
        <AnalyticsTab />
        <StrategyTab />
      </div>
    </div>
  );
}

export default PublishStep;