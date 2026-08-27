import React from 'react';
import terms from '../terms.json';

// terms.json のキー型定義
type TermKey = keyof typeof terms;

export interface TooltipProps {
  termKey?: TermKey;
  content?: React.ReactNode;
  delay?: number;
  className?: string;
  children: React.ReactNode;
}

export const Tooltip: React.FC<TooltipProps> = ({ termKey, content, delay = 0, className = '', children }) => {
  const [show, setShow] = React.useState(false);
  const timeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const termData = termKey ? terms[termKey] : null;
  const tooltipContent = content ?? (termData ? (
    <>
      <strong>{termData.term}</strong>: {termData.description}
    </>
  ) : null);

  if (!tooltipContent) return <>{children}</>;

  const handleMouseEnter = () => {
    if (delay > 0) {
      timeoutRef.current = setTimeout(() => setShow(true), delay);
    } else {
      setShow(true);
    }
  };

  const handleMouseLeave = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    setShow(false);
  };

  return (
    <span 
      className={`tooltip-container ${className}`}
      role="button"
      tabIndex={0}
      onClick={() => setShow(!show)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          setShow(!show);
        }
      }}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {children}
      {termKey && (
        <span className="tooltip-trigger">
          (?)
        </span>
      )}
      <span className={`tooltip-popup ${show ? 'visible' : ''}`}>
        {tooltipContent}
      </span>
    </span>
  );
};
