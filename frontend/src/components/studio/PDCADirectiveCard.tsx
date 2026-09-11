import React from 'react';

interface WritingDirectiveProps {
  directive: {
    dimension: string;
    severity: 'low' | 'medium' | 'high';
    target_location: string;
    current_issue: string;
    mandatory_instruction: string;
    rationale: string;
    specialist_name?: string;
  };
}

const SEVERITY_COLORS = {
  low: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', badge: 'bg-blue-100' },
  medium: { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200', badge: 'bg-yellow-100' },
  high: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', badge: 'bg-red-100' },
};

export const PDCADirectiveCard: React.FC<WritingDirectiveProps> = ({ directive }) => {
  const colors = SEVERITY_COLORS[directive.severity] || SEVERITY_COLORS.low;

  return (
    <div className={`p-4 rounded-lg border ${colors.border} ${colors.bg} shadow-sm space-y-3`}>
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${colors.badge} ${colors.text}`}>
            {directive.severity}
          </span>
          <span className="text-xs font-bold text-gray-600">{directive.dimension}</span>
        </div>
        {directive.specialist_name && (
          <span className="text-[10px] text-gray-400 italic">
            by {directive.specialist_name}
          </span>
        )}
      </div>

      <div className="space-y-2">
        <div>
          <div className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Target Location</div>
          <div className="text-sm text-gray-700">{directive.target_location}</div>
        </div>

        <div>
          <div className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Current Issue</div>
          <div className="text-sm text-gray-700">{directive.current_issue}</div>
        </div>

        <div className="p-2 bg-white rounded border border-gray-100">
          <div className="text-[11px] font-semibold text-blue-600 uppercase tracking-wider mb-1">Mandatory Instruction</div>
          <div className="text-sm font-medium text-gray-900">{directive.mandatory_instruction}</div>
        </div>

        <div>
          <div className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Rationale</div>
          <div className="text-sm text-gray-600 italic">{directive.rationale}</div>
        </div>
      </div>
    </div>
  );
};
