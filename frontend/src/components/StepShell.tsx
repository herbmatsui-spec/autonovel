import React from 'react';

interface StepShellProps {
  children: React.ReactNode;
}

export default function StepShell({ children }: StepShellProps) {
  return (
    <div className="p-6 space-y-4">
      {children}
    </div>
  );
}