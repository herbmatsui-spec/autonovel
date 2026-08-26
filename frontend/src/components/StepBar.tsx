import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Term } from '@/components/Term';

export default function StepBar({ bookId, currentStep }) {
  const navigate = useNavigate();
  const steps = [
    { id: 'theme', label: 'テーマ', icon: '🎯' },
    { id: 'outline', label: 'あらすじ', icon: '📖' },
    { id: 'write', label: '執筆', icon: '✍️' },
    { id: 'finish', label: '仕上げ', icon: '✨' },
    { id: 'publish', label: '公開', icon: '🚀' },
  ];

  return (
    <div className="flex-shrink-0 w-[200px] bg-[var(--bg-sidebar)] border-r border-[var(--border)] p-4">
      <div className="space-y-2">
        {steps.map((step) => {
          const isCurrent = step.id === currentStep;
          return (
            <button
              key={step.id}
              onClick={() => {
                if (bookId) {
                  navigate(`/book/${bookId}/${step.id}`);
                }
              }}
              className={`w-full text-left justify-start flex items-center space-x-3 p-2 rounded ${
                isCurrent
                  ? 'bg-[var(--accent)]/20 text-[var(--accent)]'
                  : 'text-[var(--text-secondary)] hover:bg-[var(--bg-muted)]'
              }`}
            >
              <span>{step.icon}</span>
              <Term term={step.label}>{step.label}</Term>
            </button>
          );
        })}
      </div>
    </div>
  );
}