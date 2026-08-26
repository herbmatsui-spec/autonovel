import React from 'react';
import { Tooltip } from '@/components/Tooltip';
import { glossary } from '@/lib/glossary';

interface TermProps {
  term: string;
  children: React.ReactNode;
}

export function Term({ term, children }: TermProps) {
  const description = glossary[term as keyof typeof glossary];
  if (description) {
    return (
      <Tooltip content={description}>
        {children}
      </Tooltip>
    );
  }
  return children;
}