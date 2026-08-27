import { PlotsTab } from '@/components/tabs/PlotsTab';

export function OutlineStep({ bookId: _bookId }: { bookId?: number } = {}) {
  return (
    <div>
      <p className="text-sm text-muted-foreground mb-2">
        AIがプロットを下書きします。よければ次へ進んでください。
      </p>
      <PlotsTab />
    </div>
  );
}

export default OutlineStep;