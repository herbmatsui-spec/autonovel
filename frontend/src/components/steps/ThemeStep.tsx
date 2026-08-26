import React from 'react';
import { PlanningTab } from '@/components/tabs/PlanningTab';

export default function ThemeStep() {
  return (
    <div>
      <p className="text-sm text-muted-foreground mb-2">
        AIが企画を下書きします。よければ次へ進んでください。
      </p>
      <PlanningTab />
    </div>
  );
}