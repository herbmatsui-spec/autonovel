import React from 'react';
import { cn } from "@/lib/utils";
import { AlertCircle, X } from "lucide-react";

interface ErrorBannerProps {
  message: string;
  onClose?: () => void;
  type?: 'error' | 'warning' | 'info';
  className?: string;
}

export const ErrorBanner = ({ 
  message, 
  onClose, 
  type = 'error', 
  className 
}: ErrorBannerProps) => {
  const themes = {
    error: "bg-destructive/15 text-destructive border-destructive/50",
    warning: "bg-yellow-500/15 text-yellow-500 border-yellow-500/50",
    info: "bg-blue-500/15 text-blue-500 border-blue-500/50",
  };

  return (
    <div 
      role="alert" 
      aria-live="assertive"
      className={cn(
        "flex items-center justify-between p-4 mb-4 border rounded-md animate-in fade-in slide-in-from-top-2",
        themes[type],
        className
      )}
    >
      <div className="flex items-center gap-3">
        <AlertCircle className="w-5 h-5 shrink-0" />
        <p className="text-sm font-medium">{message}</p>
      </div>
      {onClose && (
        <button 
          onClick={onClose}
          className="p-1 hover:bg-current/10 rounded-full transition-colors"
          aria-label="閉じる"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
};
