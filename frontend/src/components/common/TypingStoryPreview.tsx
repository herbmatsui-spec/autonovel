import React, { useState, useEffect } from 'react';

interface TypingStoryPreviewProps {
  fullText: string;
  speedMs?: number;
}

export const TypingStoryPreview: React.FC<TypingStoryPreviewProps> = ({
  fullText,
  speedMs = 25,
}) => {
  const [displayedText, setDisplayedText] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    setDisplayedText('');
    setCurrentIndex(0);
  }, [fullText]);

  useEffect(() => {
    if (currentIndex >= fullText.length) return;

    const timer = setTimeout(() => {
      setDisplayedText((prev) => prev + fullText[currentIndex]);
      setCurrentIndex((prev) => prev + 1);
    }, speedMs);

    return () => clearTimeout(timer);
  }, [currentIndex, fullText, speedMs]);

  return (
    <div className="bg-slate-950 border border-slate-800 rounded-2xl p-6 font-serif leading-relaxed text-slate-200 shadow-inner max-h-[60vh] overflow-y-auto whitespace-pre-wrap">
      {displayedText}
      <span className="inline-block w-2 h-4 bg-indigo-500 animate-pulse ml-0.5 align-middle" />
    </div>
  );
};
