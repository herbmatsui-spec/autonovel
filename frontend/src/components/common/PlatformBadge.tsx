import React from 'react';
import { CommercialPlatform } from '../../types/commercial';

interface PlatformBadgeProps {
  platform: CommercialPlatform;
  className?: string;
}

const PLATFORM_CONFIG: Record<CommercialPlatform, { color: string; label: string }> = {
  narou: { color: '#4a90e2', label: '小説家になろう' },
  kakuyomu: { color: '#ff4500', label: 'カクヨム' },
  kindle: { color: '#ff9900', label: 'Kindle' },
  kobo: { color: '#005a9c', label: 'Kobo' },
};

/**
 * プラットフォーム別の識別バッジコンポーネント
 */
export const PlatformBadge: React.FC<PlatformBadgeProps> = ({ platform, className = '' }) => {
  const config = PLATFORM_CONFIG[platform] || { color: '#888', label: platform };

  return (
    <span 
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${className}`}
      style={{ 
        backgroundColor: `${config.color}22`, // 13% opacity
        color: config.color,
        border: `1px solid ${config.color}44` // 26% opacity
      }}
    >
      {config.label}
    </span>
  );
};

export default PlatformBadge;
