import React from 'react';
import { uiAssetManifest } from '@/lib/uiAssetManifest';

interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary';
  className?: string;
  // We can also allow overriding the background image via props if needed
  backgroundImage?: string;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  onClick,
  variant = 'primary',
  className = '',
  backgroundImage,
}) => {
  // Use the provided backgroundImage prop, or fall back to the manifest, or fallback to a default color
  const bgUrl = backgroundImage || uiAssetManifest.button || '';
  const hasImage = bgUrl.length > 0;

  return (
    <button
      onClick={onClick}
      className={`
        flex items-center justify-center px-4 py-2 rounded
        ${variant === 'primary' ? 'text-white' : 'text-white'}
        hover:opacity-90
        transition-opacity
        ${className}
      `}
      style={{
        backgroundImage: hasImage ? `url(${bgUrl})` : 'none',
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        // Fallback color if no image
        backgroundColor: !hasImage && (variant === 'primary' ? '#4f46e5' : '#6b7280'),
      }}
    >
      {children}
    </button>
  );
};