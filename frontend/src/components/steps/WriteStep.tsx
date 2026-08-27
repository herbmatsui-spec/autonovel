import { WriteTab } from '@/components/tabs/WriteTab';

export function WriteStep(_props: { bookId?: number } = {}) {
  return (
    <div>
      <p className="text-sm text-muted-foreground mb-2">
        AIが本文を下書きします。よければ次へ進んでください。
      </p>
      <WriteTab />
    </div>
  );
}

export default WriteStep;