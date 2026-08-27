import { PlotsTab } from '@/components/tabs/PlotsTab';

export function OutlineStep(_props: { bookId?: number } = {}) {
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