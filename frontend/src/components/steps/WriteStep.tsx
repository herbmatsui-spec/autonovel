import React from 'react';
import { WriteTab } from '@/components/tabs/WriteTab';

export default function WriteStep() {
  return (
    <div>
      <p className="text-sm text-muted-foreground mb-2">
        AIが本文を下書きします。よければ次へ進んでください。
      </p>
      <WriteTab />
    </div>
  );
}