import React from 'react';
import { PlotsTab } from '@/components/tabs/PlotsTab';

export default function OutlineStep() {
  return (
    <div>
      <p className="text-sm text-muted-foreground mb-2">
        AIがプロットを下書きします。よければ次へ進んでください。
      </p>
      <PlotsTab />
    </div>
  );
}