import React from 'react';

interface PDCADiffViewerProps {
  beforeText: string;
  afterText: string;
}

export const PDCADiffViewer: React.FC<PDCADiffViewerProps> = ({ beforeText, afterText }) => {
  // Simple line-based diff for demonstration. 
  // In a real production app, we'd use a library like 'diff' or 'jsdiff'.
  const beforeLines = beforeText.split('\\n');
  const afterLines = afterText.split('\\n');
  
  const maxLines = Math.max(beforeLines.length, afterLines.length);

  return (
    <div className="flex flex-col gap-4 w-full">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <div className="text-xs font-bold text-gray-500 uppercase tracking-wider">Before (改善前)</div>
          <div className="p-3 bg-red-50 rounded-lg border border-red-100 font-mono text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
            {beforeLines.map((line, i) => (
              <div key={i} className={line !== afterLines[i] ? 'bg-red-200' : ''}>
                {line || ' '}
              </div>
            ))}
          </div>
        </div>
        <div className="space-y-2">
          <div className="text-xs font-bold text-gray-500 uppercase tracking-wider">After (改善後)</div>
          <div className="p-3 bg-green-50 rounded-lg border border-green-100 font-mono text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
            {afterLines.map((line, i) => (
              <div key={i} className={line !== beforeLines[i] ? 'bg-green-200' : ''}>
                {line || ' '}
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="text-[11px] text-gray-400 italic text-center">
        ※ 色付きの行は変更箇所を示しています
      </div>
    </div>
  );
};
