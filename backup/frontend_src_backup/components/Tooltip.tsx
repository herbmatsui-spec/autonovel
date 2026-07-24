import React from 'react';
import terms from '../terms.json';
import { useTermTooltip } from '../hooks/useTermTooltip';

// terms.json のキー型定義
type TermKey = keyof typeof terms;

interface TooltipProps {
  termKey: TermKey;
  children: React.ReactNode;
}

export const Tooltip: React.FC<TooltipProps> = ({ termKey, children }) => {
  const { term, description, exists } = useTermTooltip(termKey);
  const [show, setShow] = React.useState(false);

  if (!exists) return <>{children}</>;

  return (
    <span 
      className="tooltip-container"
      onClick={() => setShow(!show)}
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      {children}
      <span className="tooltip-trigger">
        (?)
      </span>
      <span className={`tooltip-popup ${show ? 'visible' : ''}`}>
        <strong>{term}</strong>: {description}
      </span>
    </span>
  );
};
