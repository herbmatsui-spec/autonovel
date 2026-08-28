import React from 'react';
import { Tooltip } from '@/components/Tooltip';
import { glossary } from '@/lib/glossary';

interface TermProps {
  term: string;
  children: React.ReactNode;
  className?: string;
}

export function Term({ term, children, className }: TermProps) {
  const description = glossary[term as keyof typeof glossary];
  if (description) {
    return (
      <Tooltip content={description}>
        <span className={className}>{children}</span>
      </Tooltip>
    );
  }
  if (className) {
    return <span className={className}>{children}</span>;
  }
  return <>{children}</>;
}