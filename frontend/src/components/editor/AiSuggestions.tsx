import React from "react";

interface AiSuggestionsProps {
  suggestions: string[];
  onApplySuggestion: (sug: string) => void;
}

export const AiSuggestions: React.FC<AiSuggestionsProps> = ({
  suggestions,
  onApplySuggestion,
}) => {
  if (suggestions.length === 0) return null;

  return (
    <div style={{ marginTop: "16px" }}>
      <div style={{ display: "flex", alignItems: "center", marginBottom: "8px", gap: "6px" }}>
        <span style={{ fontSize: "1.1rem" }}>💡</span>
        <span className="label" style={{ marginBottom: 0 }}>次話へのAI提案 (クリックで本文へ反映)</span>
      </div>
      <div className="chips">
        {suggestions.map((s, idx) => (
          <button
            type="button"
            className="chip chip--interactive"
            key={idx}
            onClick={() => onApplySuggestion(s)}
            title="クリックしてエディタの末尾に展開を追加"
          >
            ＋ {s}
          </button>
        ))}
      </div>
    </div>
  );
};
