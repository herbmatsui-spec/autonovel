import React from 'react';

interface PDCADiffViewerProps {
  paragraphs: Array<{
    index: number;
    original: string;
    patched: string;
    reason: string;
  }>;
}

export const PDCADiffViewer: React.FC<PDCADiffViewerProps> = ({ paragraphs }) => {
  return (
    <div className="space-y-6">
      {paragraphs.map((p) => (
        <div key={p.index} className="border-l-4 border-yellow-400 bg-yellow-50 p-4 rounded-lg">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <span className="text-xs font-medium text-gray-600">
              Paragraph {p.index}
            </span>
            <span className="px-2 py-0.5 bg-yellow-200 text-yellow-800 text-xs rounded">
              {p.reason}
            </span>
          </div>
          <div className="prose prose-sm max-w-none">
            <p className="mb-2 font-semibold text-gray-800">Original:</p>
            <p className="mb-4 bg-white p-3 rounded border border-gray-200 font-mono text-sm whitespace-pre-wrap">
              {p.original}
            </p>
            <p className="mb-2 font-semibold text-gray-800">Patched:</p>
            <p className="bg-yellow-100 p-3 rounded border border-yellow-200 font-mono text-sm whitespace-pre-wrap">
              {p.patched}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
};