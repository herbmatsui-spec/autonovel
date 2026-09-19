import React from 'react';
import { ForeshadowingScope } from '@/models/foreshadowing_status'; // Adjust the import path as needed

interface ForeshadowingScopeBadgeProps {
  scope: ForeshadowingScope;
}

const ForeshadowingScopeBadge: React.FC<ForeshadowingScopeBadgeProps> = ({ scope }) => {
  const getBadge = () => {
    switch (scope) {
      case ForeshadowingScope.SHORT_TERM:
        return <span className="badge">⚡ 即回収</span>;
      case ForeshadowingScope.LONG_TERM:
        return <span className="badge">🎯 1巻クライマックス</span>;
      default:
        return <span className="badge">{scope}</span>;
    }
  };

  return (
    <div>
      {getBadge()}
    </div>
  );
};

export default ForeshadowingScopeBadge;