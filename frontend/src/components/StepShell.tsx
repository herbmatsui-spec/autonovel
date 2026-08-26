import React from 'react';
import { Tooltip } from '@/components/Tooltip';

// StepShell provides a consistent wrapper for each step:
// - Title (passed as prop? we'll let children decide)
// - Optional description
// - Tooltip wrapper for expert terms
// We'll keep it simple: just a container with padding.
export default function StepShell({ children }) {
  return (
    <div className="p-6 space-y-4">
      {children}
    </div>
  );
}